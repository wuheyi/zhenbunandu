from __future__ import annotations

from pathlib import Path
import json

import httpx

from fastapi.testclient import TestClient

from zhenbunandu.app import app, session as api_session
from zhenbunandu.autoplay import run_autoplay_batch, run_single_autoplay
from zhenbunandu.content import load_content
from zhenbunandu.db import GameDB
from zhenbunandu.llm import DEFAULT_LLM_MODEL, LLMClient
from zhenbunandu.session import GameSession


def make_session(tmp_path: Path) -> GameSession:
    db = GameDB(tmp_path / "game.db")
    game = GameSession(db=db, content=load_content())
    game.new_game()
    return game


def test_new_game_initializes_core_tables(tmp_path: Path) -> None:
    game = make_session(tmp_path)
    state = game.state()
    assert state["game"]["turn"] == 1
    assert {metric["key"] for metric in state["metrics"]} >= {"国库", "内帑", "京城粮", "民心", "君威"}
    assert len(state["events"]) >= 3
    assert any(minister["id"] == "li_gang" for minister in state["ministers"])
    assert len(state["logistics_routes"]) == 3
    assert any(node["id"] == "capital_grain_market" for route in state["logistics_routes"] for node in route["nodes"])
    assert len(state["faction_clocks"]) >= 5
    assert state["faction_retaliations"] == []
    assert {option["action"] for option in state["diplomacy_options"]} >= {"stall", "tribute", "hardline", "divide"}
    assert state["diplomacy"]["status"] == "未接触"
    assert state["diplomacy_terms"] == []
    assert state["diplomacy_incidents"] == []
    assert state["guidance"]["stage"] == "初登大宝"
    assert any(tip["target"] == "minister:li_gang" for tip in state["guidance"]["tips"])
    assert state["postmortem"]["status"] == "active"


def test_first_turn_creates_directives_secret_and_case(tmp_path: Path) -> None:
    game = make_session(tmp_path)
    li = game.minister_chat("li_gang", "守城要谁办")
    hu = game.minister_chat("finance_minister", "禁军饷怎么办")
    spy = game.minister_chat("imperial_city司", "暗查账册")
    assert li["proposed_directive"]["title"] == "任李纲临督宣化门城防"
    assert hu["proposed_directive"]["title"] == "开内帑补禁军急饷"
    assert spy["secret_order"]["title"] == "密查禁军军饷账册"

    result = game.resolve_turn()
    state = result["state"]
    assert any(item["id"] == "dongcang副册" for item in state["evidence"])
    assert any(case["id"] == "forbidden_army_pay_case" and case["status"] == "ready" for case in state["court_cases"])
    assert state["game"]["turn"] == 2


def test_judgment_changes_case_and_memory(tmp_path: Path) -> None:
    game = make_session(tmp_path)
    game.minister_chat("imperial_city司", "查禁军账册")
    game.resolve_turn()
    judged = game.judge_case("forbidden_army_pay_case", "追银")
    assert judged["case"]["status"] == "judged"
    state = judged["state"]
    assert state["memories"][0]["title"] == "禁军欠饷案殿前裁断"
    assert next(metric for metric in state["metrics"] if metric["key"] == "君威")["value"] > 48


def test_debate_creates_strategy_drafts_and_anchor_events(tmp_path: Path) -> None:
    game = make_session(tmp_path)
    result = game.create_debate("战和与勤王")
    state = result["state"]
    titles = {directive["title"] for directive in state["directives"]}
    assert {"发勤王诏催西军入援", "遣使假议和拖延金军", "开仓平粜稳京城粮价"} <= titles
    resolved = game.resolve_turn()["state"]
    assert any(event["id"] == "turn2_jin_envoy" for event in resolved["events"])
    assert resolved["diplomacy"]["status"] == "金使入城"


def test_route_actions_and_faction_clocks_update_state(tmp_path: Path) -> None:
    game = make_session(tmp_path)
    initial_state = game.state()
    initial_route = next(route for route in initial_state["logistics_routes"] if route["id"] == "jianghuai_grain_to_bianjing")
    escorted = game.route_action("jianghuai_grain_to_bianjing", "escort")["state"]
    escorted_route = next(route for route in escorted["logistics_routes"] if route["id"] == "jianghuai_grain_to_bianjing")
    assert escorted_route["risk"] < initial_route["risk"]
    assert escorted_route["escort"] > initial_route["escort"]
    assert escorted["ledger"][0]["category"] == "路线行动"

    rewarded = game.route_action("shaanxi_relief_army", "reward")["state"]
    assert rewarded["siege"]["qinwang_response"] > escorted["siege"]["qinwang_response"]
    western_clock = next(clock for clock in rewarded["faction_clocks"] if clock["id"] == "western_army_grievance")
    assert western_clock["value"] < 22

    before_clock = next(clock for clock in rewarded["faction_clocks"] if clock["id"] == "transport_slowdown")
    mitigated = game.mitigate_faction_clock("transport_slowdown", "appease")["state"]
    after_clock = next(clock for clock in mitigated["faction_clocks"] if clock["id"] == "transport_slowdown")
    assert after_clock["value"] < before_clock["value"]


def test_route_node_actions_update_nodes_and_route(tmp_path: Path) -> None:
    game = make_session(tmp_path)
    before = game.state()
    shaanxi = next(route for route in before["logistics_routes"] if route["id"] == "shaanxi_relief_army")
    crossing = next(node for node in shaanxi["nodes"] if node["id"] == "hezhong_crossing")

    cleared = game.route_action("shaanxi_relief_army", "clear_intercept", "hezhong_crossing")["state"]
    after_route = next(route for route in cleared["logistics_routes"] if route["id"] == "shaanxi_relief_army")
    after_crossing = next(node for node in after_route["nodes"] if node["id"] == "hezhong_crossing")
    assert after_route["eta"] < shaanxi["eta"]
    assert after_crossing["risk"] < crossing["risk"]
    assert after_crossing["progress"] > crossing["progress"]
    assert cleared["siege"]["qinwang_response"] > before["siege"]["qinwang_response"]


def test_grain_credit_action_lowers_grain_price_and_recovers_market(tmp_path: Path) -> None:
    game = make_session(tmp_path)
    before = game.state()
    grain_route = next(route for route in before["logistics_routes"] if route["id"] == "jianghuai_grain_to_bianjing")
    market = next(node for node in grain_route["nodes"] if node["id"] == "capital_grain_market")

    restored = game.route_action("jianghuai_grain_to_bianjing", "restore_credit", "capital_grain_market")["state"]
    after_route = next(route for route in restored["logistics_routes"] if route["id"] == "jianghuai_grain_to_bianjing")
    after_market = next(node for node in after_route["nodes"] if node["id"] == "capital_grain_market")
    assert after_market["risk"] < market["risk"]
    assert after_market["progress"] > market["progress"]
    assert restored["siege"]["grain_price"] < before["siege"]["grain_price"]


def test_faction_retaliation_can_secure_evidence(tmp_path: Path) -> None:
    game = make_session(tmp_path)
    game.db.ensure_evidence_and_case(1)
    game.db.change_faction_clock("transport_slowdown", 60)

    created = game.resolve_turn()["state"]
    retaliation = next(item for item in created["faction_retaliations"] if item["kind"] == "destroy_evidence")
    evidence_before = next(item for item in created["evidence"] if item["id"] == "dongcang副册")
    clock_before = next(clock for clock in created["faction_clocks"] if clock["id"] == "transport_slowdown")
    assert retaliation["status"] == "active"
    assert retaliation["evidence_target"] == "dongcang副册"

    secured = game.faction_retaliation_action(retaliation["id"], "secure_evidence")["state"]
    secured_retaliation = next(item for item in secured["faction_retaliations"] if item["id"] == retaliation["id"])
    evidence_after = next(item for item in secured["evidence"] if item["id"] == "dongcang副册")
    clock_after = next(clock for clock in secured["faction_clocks"] if clock["id"] == "transport_slowdown")
    assert secured_retaliation["status"] == "resolved"
    assert evidence_after["status"] == "secured"
    assert evidence_after["reliability"] > evidence_before["reliability"]
    assert clock_after["value"] < clock_before["value"]
    assert secured["ledger"][0]["category"] == "护证密支"


def test_faction_retaliation_damages_evidence_when_ignored(tmp_path: Path) -> None:
    game = make_session(tmp_path)
    game.db.ensure_evidence_and_case(1)
    game.db.change_faction_clock("transport_slowdown", 60)
    created = game.resolve_turn()["state"]
    retaliation = next(item for item in created["faction_retaliations"] if item["kind"] == "destroy_evidence")
    evidence_before = next(item for item in created["evidence"] if item["id"] == "dongcang副册")
    case_before = next(case for case in created["court_cases"] if case["id"] == "forbidden_army_pay_case")
    game.db.conn.execute("UPDATE faction_retaliations SET due_turn = 1 WHERE id = ?", (retaliation["id"],))

    resolved = game.resolve_turn()["state"]
    triggered = next(item for item in resolved["faction_retaliations"] if item["id"] == retaliation["id"])
    evidence_after = next(item for item in resolved["evidence"] if item["id"] == "dongcang副册")
    case_after = next(case for case in resolved["court_cases"] if case["id"] == "forbidden_army_pay_case")
    assert triggered["status"] == "triggered"
    assert evidence_after["status"] == "compromised"
    assert evidence_after["strength"] < evidence_before["strength"]
    assert case_after["risk"] > case_before["risk"]
    assert any("毁证" in warning for warning in resolved["reports"][0]["warnings"])


def test_diplomacy_actions_update_pressure_and_records(tmp_path: Path) -> None:
    game = make_session(tmp_path)
    before = game.state()
    result = game.diplomacy_action("stall")
    after = result["state"]
    assert after["diplomacy"]["status"] == "拖延谈判"
    assert after["diplomacy"]["impatience"] < before["diplomacy"]["impatience"]
    assert after["diplomacy"]["leverage"] > before["diplomacy"]["leverage"]
    assert after["ledger"][0]["category"] == "外交礼物"

    divided = game.diplomacy_action("divide")["state"]
    assert divided["diplomacy"]["internal_tension"] > after["diplomacy"]["internal_tension"]
    assert divided["ledger"][0]["visibility"] == "秘密"


def test_diplomacy_terms_can_be_created_and_honored(tmp_path: Path) -> None:
    game = make_session(tmp_path)
    tribute = game.diplomacy_action("tribute")["state"]
    term = tribute["diplomacy_terms"][0]
    assert term["title"] == "犒军暂缓约"
    assert term["status"] == "active"
    assert any(option["action"] == "honor_terms" for option in tribute["diplomacy_options"])

    honored = game.diplomacy_action("honor_terms")["state"]
    honored_term = honored["diplomacy_terms"][0]
    assert honored_term["compliance"] > term["compliance"]
    assert honored_term["breach_risk"] < term["breach_risk"]
    assert honored["diplomacy"]["status"] == "补足条款"
    assert honored["ledger"][0]["category"] == "外交履约"


def test_diplomacy_term_breach_resolves_into_report_and_event(tmp_path: Path) -> None:
    game = make_session(tmp_path)
    game.diplomacy_action("stall")
    term = game.state()["diplomacy_terms"][0]
    game.db.conn.execute(
        "UPDATE diplomacy_terms SET due_turn = 1, compliance = 15, breach_risk = 85 WHERE id = ?",
        (term["id"],),
    )

    resolved = game.resolve_turn()["state"]
    breached = resolved["diplomacy_terms"][0]
    assert breached["status"] == "breached"
    assert "失信" in breached["result"]
    incident = resolved["diplomacy_incidents"][0]
    assert incident["status"] == "active"
    assert incident["title"] == "金营扣留宋使"
    assert "草约" in incident["treaty_text"]
    assert any(option["action"] == "redeem_envoy" for option in resolved["diplomacy_options"])
    assert any(event["id"].startswith("diplomacy_breach_") for event in resolved["events"])
    assert any("外交条款失信" in warning for warning in resolved["reports"][0]["warnings"])


def test_detained_envoy_can_be_redeemed_or_escalate(tmp_path: Path) -> None:
    game = make_session(tmp_path)
    game.diplomacy_action("stall")
    term = game.state()["diplomacy_terms"][0]
    game.db.conn.execute(
        "UPDATE diplomacy_terms SET due_turn = 1, compliance = 15, breach_risk = 85 WHERE id = ?",
        (term["id"],),
    )
    breached = game.resolve_turn()["state"]
    incident = breached["diplomacy_incidents"][0]

    redeemed = game.diplomacy_action("redeem_envoy")["state"]
    resolved_incident = redeemed["diplomacy_incidents"][0]
    assert resolved_incident["status"] == "resolved"
    assert "得返" in resolved_incident["resolution"]
    assert redeemed["diplomacy"]["status"] == "赎回使节"
    assert redeemed["ledger"][0]["category"] == "扣使赎回"

    game = make_session(tmp_path)
    game.diplomacy_action("stall")
    term = game.state()["diplomacy_terms"][0]
    game.db.conn.execute(
        "UPDATE diplomacy_terms SET due_turn = 1, compliance = 15, breach_risk = 85 WHERE id = ?",
        (term["id"],),
    )
    game.resolve_turn()
    incident = game.state()["diplomacy_incidents"][0]
    game.db.conn.execute("UPDATE diplomacy_incidents SET deadline_turn = 1 WHERE id = ?", (incident["id"],))
    escalated = game.resolve_turn()["state"]
    escalated_incident = escalated["diplomacy_incidents"][0]
    assert escalated_incident["status"] == "escalated"
    assert any(event["id"].startswith("diplomacy_envoy_escalation_") for event in escalated["events"])
    assert any("扣使风波升级" in warning for warning in escalated["reports"][0]["warnings"])


def test_second_turn_can_generate_night_attack_report(tmp_path: Path) -> None:
    game = make_session(tmp_path)
    game.minister_chat("li_gang", "守城")
    game.minister_chat("finance_minister", "补饷")
    game.create_debate("战和与勤王")
    game.resolve_turn()
    state = game.resolve_turn()["state"]
    assert any(report["title"] == "宣化门夜攻" for report in state["battle_reports"])
    assert state["game"]["turn"] == 3


def test_api_sse_resolution_returns_done_event() -> None:
    api_session.new_game()
    client = TestClient(app)
    client.post("/api/ministers/li_gang/chat", json={"message": "请李纲守城"})
    response = client.post("/api/decree/issue/stream")
    assert response.status_code == 200
    assert "event: done" in response.text


def test_api_court_debate_endpoint() -> None:
    api_session.new_game()
    client = TestClient(app)
    response = client.post("/api/court/debate", json={"topic": "战和与勤王"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["state"]["court_debates"][0]["topic"] == "战和与勤王"


def test_api_route_action_and_clock_mitigation_endpoints() -> None:
    api_session.new_game()
    client = TestClient(app)
    route_response = client.post(
        "/api/routes/jianghuai_grain_to_bianjing/action",
        json={"action": "restore_credit", "node_id": "capital_grain_market"},
    )
    assert route_response.status_code == 200
    assert route_response.json()["state"]["logistics_routes"][0]["status"] == "恢复信用"
    clock_response = client.post("/api/faction_clocks/grain_market_strike/mitigate", json={"action": "appease"})
    assert clock_response.status_code == 200
    assert next(clock for clock in clock_response.json()["state"]["faction_clocks"] if clock["id"] == "grain_market_strike")["value"] <= 4


def test_api_faction_retaliation_action_endpoint() -> None:
    api_session.new_game()
    api_session.db.ensure_evidence_and_case(1)
    api_session.db.change_faction_clock("transport_slowdown", 60)
    api_session.resolve_turn()
    state = api_session.state()
    retaliation = next(item for item in state["faction_retaliations"] if item["kind"] == "destroy_evidence")

    client = TestClient(app)
    response = client.post(f"/api/faction_retaliations/{retaliation['id']}/action", json={"action": "split_clique"})
    assert response.status_code == 200
    payload = response.json()
    updated = next(item for item in payload["state"]["faction_retaliations"] if item["id"] == retaliation["id"])
    assert updated["status"] == "resolved"
    assert payload["state"]["ledger"][0]["category"] == "分化胁从"


def test_api_diplomacy_action_endpoint() -> None:
    api_session.new_game()
    client = TestClient(app)
    response = client.post("/api/diplomacy/action", json={"action": "hardline"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["state"]["diplomacy"]["status"] == "强硬拒使"
    assert payload["state"]["diplomacy"]["leverage"] > 22
    assert payload["state"]["siege"]["defender_will"] > 45


def test_autoplay_seed_scenarios_change_opening_pressure() -> None:
    standard = run_single_autoplay("defender", "jingkang-standard-001", max_turns=0)
    treasury_crash = run_single_autoplay("defender", "treasury-crash-001", max_turns=0)
    grain_crisis = run_single_autoplay("defender", "grain-crisis-001", max_turns=0)

    assert treasury_crash["seed_profile"]["registered"]
    assert treasury_crash["final"]["treasury"] < standard["final"]["treasury"]
    assert grain_crisis["final"]["grain_price"] > standard["final"]["grain_price"]
    assert grain_crisis["final"]["max_route_risk"] > standard["final"]["max_route_risk"]


def test_autoplay_batch_writes_balance_reports(tmp_path: Path) -> None:
    output_dir = tmp_path / "balance"
    result = run_autoplay_batch(
        strategies=["defender", "diplomat"],
        seeds=["jingkang-standard-001", "jin-rush-001"],
        max_turns=2,
        output_dir=output_dir,
    )

    assert result["summary"]["total_runs"] == 4
    assert result["summary"]["avg_turns"] == 2
    assert result["summary"]["strategy_rows"][0]["top_actions"]
    assert (output_dir / "summary.md").exists()
    assert (output_dir / "metrics.csv").exists()
    assert (output_dir / "endings.json").exists()
    assert (output_dir / "route_compare.md").exists()
    assert (output_dir / "anomaly_report.md").exists()
    assert len(list((output_dir / "sample_turns").glob("*.json"))) == 4


def test_llm_without_key_uses_fallback(tmp_path: Path) -> None:
    game = make_session(tmp_path)
    game.save_llm({"base_url": "https://api.deepseek.com", "model": DEFAULT_LLM_MODEL, "api_key": ""})
    status = game.menu_status()
    assert not status["has_api_key"]
    assert "api_key" not in status["llm"]
    result = game.test_llm()
    assert not result["ok"]
    assert "确定性规则" in result["sample"]


def test_llm_client_posts_openai_compatible_payload() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == "https://api.deepseek.com/chat/completions"
        assert request.headers["authorization"] == "Bearer test-key"
        body = json.loads(request.content)
        assert body["model"] == DEFAULT_LLM_MODEL
        assert body["messages"][0]["role"] == "system"
        return httpx.Response(200, json={"choices": [{"message": {"content": "御案已通，仍守汴京。"}}]})

    client = LLMClient(
        {"base_url": "https://api.deepseek.com", "model": DEFAULT_LLM_MODEL, "api_key": "test-key"},
        transport=httpx.MockTransport(handler),
    )
    result = client.complete(
        [{"role": "system", "content": "测试"}, {"role": "user", "content": "通了吗"}],
        fallback="fallback",
    )
    assert result.used_llm
    assert result.text == "御案已通，仍守汴京。"
