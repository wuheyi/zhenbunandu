from __future__ import annotations

from pathlib import Path
import json

import httpx

from fastapi.testclient import TestClient

from zhenbunandu.app import app, session as api_session
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
    assert len(state["faction_clocks"]) >= 5
    assert {option["action"] for option in state["diplomacy_options"]} >= {"stall", "tribute", "hardline", "divide"}
    assert state["diplomacy"]["status"] == "未接触"
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
    route_response = client.post("/api/routes/jianghuai_grain_to_bianjing/action", json={"action": "subsidy"})
    assert route_response.status_code == 200
    assert route_response.json()["state"]["logistics_routes"][0]["status"] == "保价催运"
    clock_response = client.post("/api/faction_clocks/grain_market_strike/mitigate", json={"action": "appease"})
    assert clock_response.status_code == 200
    assert next(clock for clock in clock_response.json()["state"]["faction_clocks"] if clock["id"] == "grain_market_strike")["value"] <= 4


def test_api_diplomacy_action_endpoint() -> None:
    api_session.new_game()
    client = TestClient(app)
    response = client.post("/api/diplomacy/action", json={"action": "hardline"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["state"]["diplomacy"]["status"] == "强硬拒使"
    assert payload["state"]["diplomacy"]["leverage"] > 22
    assert payload["state"]["siege"]["defender_will"] > 45


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
