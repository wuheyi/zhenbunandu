from __future__ import annotations

import argparse
import csv
import json
import random
import tempfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from .content import GameContent, load_content
from .db import GameDB
from .session import GameSession


DEFAULT_STRATEGIES = ["defender", "auditor", "diplomat", "qinwang", "livelihood", "iron_fist", "balanced", "random"]
DEFAULT_SEEDS = [
    "jingkang-standard-001",
    "treasury-crash-001",
    "grain-crisis-001",
    "pro-peace-surge-001",
    "faction-backlash-001",
    "jin-rush-001",
    "qinwang-delay-001",
    "city-gate-risk-001",
]

STRATEGY_LABELS = {
    "defender": "守城派",
    "auditor": "清算派",
    "diplomat": "议和拖延派",
    "qinwang": "勤王派",
    "livelihood": "民生派",
    "iron_fist": "铁腕派",
    "balanced": "平衡派",
    "random": "随机派",
}

SEED_SCENARIOS: dict[str, dict[str, Any]] = {
    "jingkang-standard-001": {"summary": "标准靖康压力。"},
    "treasury-crash-001": {
        "summary": "财政亏空，补饷与外交开支都会更吃紧。",
        "metrics": {"国库": -28, "内帑": -8, "君威": -3},
        "issues": {"investigate_pay": 12},
        "clocks": {"transport_slowdown": 12},
    },
    "grain-crisis-001": {
        "summary": "粮价先涨，江淮粮道与粮行反扑同步恶化。",
        "metrics": {"京城粮": -20, "民心": -7},
        "siege": {"grain_price": 36},
        "routes": {"jianghuai_grain_to_bianjing": {"risk": 18, "eta": 2, "current_load": -6}},
        "clocks": {"grain_market_strike": 35, "transport_slowdown": 18},
    },
    "pro-peace-surge-001": {
        "summary": "主和声浪提前抬头，守城意志和君威受压。",
        "metrics": {"君威": -8},
        "siege": {"peace_pressure": 28, "defender_will": -8},
        "diplomacy": {"trust": 8, "demand_severity": 10},
        "clocks": {"southern_flight_talk": 38, "li_gang_removal": 20},
    },
    "faction-backlash-001": {
        "summary": "清算与战时动员已经激起多路反扑。",
        "metrics": {"君威": -4},
        "siege": {"peace_pressure": 12},
        "clocks": {"transport_slowdown": 25, "li_gang_removal": 30, "western_army_grievance": 20},
    },
    "jin-rush-001": {
        "summary": "金军压境更快，城防、城门和外交耐心同步承压。",
        "siege": {"jin_pressure": 30, "city_defense": -8, "gate_risk": 15, "fire_risk": 8},
        "diplomacy": {"impatience": 20, "demand_severity": 8},
    },
    "qinwang-delay-001": {
        "summary": "勤王兵迟疑，陕西路线风险和西军怨望偏高。",
        "siege": {"qinwang_response": -12},
        "routes": {"shaanxi_relief_army": {"risk": 18, "eta": 3, "current_load": -5}},
        "clocks": {"western_army_grievance": 42},
        "issues": {"qinwang_call": -10},
    },
    "city-gate-risk-001": {
        "summary": "城门内应与火患风险偏高，守城派需要更早补位。",
        "siege": {"gate_risk": 30, "city_defense": -5, "fire_risk": 12},
        "gates": {"risk": 16, "condition": -6},
        "clocks": {"li_gang_removal": 16},
    },
}


def metric_map(state: dict[str, Any]) -> dict[str, int]:
    return {item["key"]: int(item["value"]) for item in state["metrics"]}


def issue_map(state: dict[str, Any]) -> dict[str, int]:
    return {item["id"]: int(item["value"]) for item in state["issues"]}


def snapshot_state(state: dict[str, Any]) -> dict[str, Any]:
    metrics = metric_map(state)
    issues = issue_map(state)
    siege = state["siege"]
    diplomacy = state["diplomacy"]
    clocks = state.get("faction_clocks", [])
    routes = state.get("logistics_routes", [])
    return {
        "turn": int(state["game"]["turn"]),
        "phase": state["game"]["phase"],
        "ended": bool(state["game"]["ended"]),
        "ending": state["game"].get("ending", ""),
        "treasury": metrics.get("国库", 0),
        "palace": metrics.get("内帑", 0),
        "grain": metrics.get("京城粮", 0),
        "public_support": metrics.get("民心", 0),
        "authority": metrics.get("君威", 0),
        "city_defense": int(siege.get("city_defense", 0)),
        "defender_will": int(siege.get("defender_will", 0)),
        "jin_pressure": int(siege.get("jin_pressure", 0)),
        "peace_pressure": int(siege.get("peace_pressure", 0)),
        "grain_price": int(siege.get("grain_price", 0)),
        "qinwang_response": int(siege.get("qinwang_response", 0)),
        "diplomacy_status": diplomacy.get("status", ""),
        "demand_severity": int(diplomacy.get("demand_severity", 0)),
        "diplomacy_impatience": int(diplomacy.get("impatience", 0)),
        "diplomacy_leverage": int(diplomacy.get("leverage", 0)),
        "discipline_guards": issues.get("discipline_guards", 0),
        "investigate_pay": issues.get("investigate_pay", 0),
        "qinwang_call": issues.get("qinwang_call", 0),
        "max_faction_clock": max((int(clock.get("value", 0)) for clock in clocks), default=0),
        "max_route_risk": max((int(route.get("risk", 0)) for route in routes), default=0),
    }


def apply_seed_scenario(game: GameSession, seed: str) -> dict[str, Any]:
    scenario = SEED_SCENARIOS.get(seed, {"summary": "未登记种子，仅作为随机决策种子使用。"})
    with game.db.conn:
        for key, delta in scenario.get("metrics", {}).items():
            game.db.change_metric(key, delta)
        for key, delta in scenario.get("siege", {}).items():
            high = 300 if key == "grain_price" else 100
            game.db.change_siege(key, delta, high=high)
        for key, delta in scenario.get("diplomacy", {}).items():
            game.db.change_diplomacy(key, delta)
        for issue_id, delta in scenario.get("issues", {}).items():
            game.db.change_issue(issue_id, delta)
        for clock_id, delta in scenario.get("clocks", {}).items():
            game.db.change_faction_clock(clock_id, delta)
        for route_id, changes in scenario.get("routes", {}).items():
            game.db.change_route(route_id, changes)
        gate_changes = scenario.get("gates")
        if gate_changes:
            game.db.conn.execute(
                """UPDATE city_gates
                   SET risk = MIN(100, MAX(0, risk + ?)),
                       condition = MIN(100, MAX(0, condition + ?))
                   WHERE status IN ('危', '疑')""",
                (int(gate_changes.get("risk", 0)), int(gate_changes.get("condition", 0))),
            )
    return {
        "id": seed,
        "summary": scenario["summary"],
        "registered": seed in SEED_SCENARIOS,
    }


def safe_action(actions: list[str], label: str, fn) -> None:
    try:
        fn()
        actions.append(label)
    except (KeyError, ValueError):
        actions.append(f"{label}:跳过")


def do_debate(game: GameSession, actions: list[str]) -> None:
    safe_action(actions, "开朝议", lambda: game.create_debate("战和与勤王"))


def do_route(game: GameSession, actions: list[str], route_id: str, action: str, label: str) -> None:
    safe_action(actions, label, lambda: game.route_action(route_id, action))


def do_diplomacy(game: GameSession, actions: list[str], action: str, label: str) -> None:
    safe_action(actions, label, lambda: game.diplomacy_action(action))


def do_case_if_ready(game: GameSession, actions: list[str]) -> None:
    ready = next((case for case in game.state()["court_cases"] if case["status"] == "ready"), None)
    if ready:
        safe_action(actions, "殿前追赃", lambda: game.judge_case(ready["id"], "下狱追银"))


def play_strategy_turn(game: GameSession, strategy: str, rng: random.Random) -> list[str]:
    state = game.state()
    actions: list[str] = []

    if strategy == "defender":
        safe_action(actions, "召李纲守城", lambda: game.minister_chat("li_gang", "守城要谁办"))
        safe_action(actions, "召户部补饷", lambda: game.minister_chat("finance_minister", "禁军饷怎么办"))
        do_route(game, actions, "jianghuai_grain_to_bianjing", "escort", "护送粮道")
        do_diplomacy(game, actions, "hardline", "强硬拒使")
    elif strategy == "auditor":
        safe_action(actions, "皇城司查账", lambda: game.minister_chat("imperial_city司", "暗查账册"))
        safe_action(actions, "召户部核账", lambda: game.minister_chat("finance_minister", "禁军饷怎么办"))
        do_case_if_ready(game, actions)
        do_route(game, actions, "jianghuai_grain_to_bianjing", "audit", "粮道查账")
    elif strategy == "diplomat":
        safe_action(actions, "召主和宰执", lambda: game.minister_chat("peace_chancellor", "如何拖延金军"))
        do_diplomacy(game, actions, "stall", "假议和拖延")
        do_debate(game, actions)
        do_route(game, actions, "shaanxi_relief_army", "envoy", "遣使催勤王")
    elif strategy == "qinwang":
        do_debate(game, actions)
        do_route(game, actions, "shaanxi_relief_army", "reward", "加赏西军")
        do_route(game, actions, "shaanxi_relief_army", "envoy", "遣使催西军")
        do_diplomacy(game, actions, "hardline", "强硬稳军心")
    elif strategy == "livelihood":
        safe_action(actions, "召开封府平粜", lambda: game.minister_chat("kaifeng_prefect", "粮价怎么办"))
        do_route(game, actions, "jianghuai_grain_to_bianjing", "subsidy", "保价催粮")
        safe_action(actions, "安抚粮行", lambda: game.mitigate_faction_clock("grain_market_strike", "appease"))
        do_diplomacy(game, actions, "stall", "拖延争粮时")
    elif strategy == "iron_fist":
        safe_action(actions, "整肃夜值", lambda: game.minister_chat("guard_representative", "军纪怎么整"))
        safe_action(actions, "皇城司密查", lambda: game.minister_chat("imperial_city司", "查禁军账册"))
        do_case_if_ready(game, actions)
        do_diplomacy(game, actions, "hardline", "强硬拒使")
        do_route(game, actions, "jianghuai_grain_to_bianjing", "audit", "查粮运")
    elif strategy == "balanced":
        metrics = metric_map(state)
        siege = state["siege"]
        if int(siege["city_defense"]) <= 48:
            safe_action(actions, "召李纲守城", lambda: game.minister_chat("li_gang", "守城要谁办"))
        if int(siege["defender_will"]) <= 50 or metrics.get("国库", 0) >= 20:
            safe_action(actions, "补禁军急饷", lambda: game.minister_chat("finance_minister", "禁军饷怎么办"))
        if int(siege["grain_price"]) >= 125:
            safe_action(actions, "开仓平粜", lambda: game.minister_chat("kaifeng_prefect", "粮价怎么办"))
            do_route(game, actions, "jianghuai_grain_to_bianjing", "subsidy", "保价催粮")
        if int(siege["qinwang_response"]) < 45:
            do_debate(game, actions)
            do_route(game, actions, "shaanxi_relief_army", "reward", "加赏勤王")
        if int(siege["jin_pressure"]) >= 62:
            do_diplomacy(game, actions, "stall", "外交拖延")
        do_case_if_ready(game, actions)
    else:
        random_actions = [
            lambda: safe_action(actions, "随机召李纲", lambda: game.minister_chat("li_gang", "本月急务")),
            lambda: safe_action(actions, "随机召户部", lambda: game.minister_chat("finance_minister", "本月急务")),
            lambda: safe_action(actions, "随机密查", lambda: game.minister_chat("imperial_city司", "查账")),
            lambda: do_debate(game, actions),
            lambda: do_route(game, actions, "jianghuai_grain_to_bianjing", rng.choice(["escort", "subsidy", "audit"]), "随机粮道行动"),
            lambda: do_route(game, actions, "shaanxi_relief_army", rng.choice(["reward", "envoy"]), "随机勤王行动"),
            lambda: do_diplomacy(game, actions, rng.choice(["stall", "hardline", "divide"]), "随机外交行动"),
            lambda: do_case_if_ready(game, actions),
        ]
        for action in rng.sample(random_actions, k=3):
            action()

    if not actions:
        actions.append("观望")
    return actions


def detect_anomalies(run: dict[str, Any]) -> list[str]:
    anomalies: list[str] = []
    steps = run["steps"]
    final = run["final"]
    if final["ended"] and final["turn"] <= 4:
        anomalies.append("early-collapse")
    if any(step["treasury"] <= 0 and step["grain"] <= 0 and step["turn"] <= 4 for step in steps):
        anomalies.append("resource-double-crash")
    jin_values = [step["jin_pressure"] for step in steps]
    for index in range(len(jin_values) - 2):
        if jin_values[index + 2] - jin_values[index] >= 45:
            anomalies.append("jin-pressure-spike")
            break
    if all(step["peace_pressure"] < 25 for step in steps):
        anomalies.append("peace-pressure-invisible")
    if max((step["max_faction_clock"] for step in steps), default=0) < 20:
        anomalies.append("faction-clocks-invisible")
    if final["treasury"] >= 80:
        anomalies.append("treasury-runaway")
    if final["qinwang_response"] >= 85 and run["strategy"] == "qinwang":
        anomalies.append("qinwang-possibly-too-strong")
    return anomalies


def run_single_autoplay(
    strategy: str,
    seed: str,
    *,
    max_turns: int = 5,
    content: GameContent | None = None,
) -> dict[str, Any]:
    rng = random.Random(f"{strategy}:{seed}")
    loaded_content = content or load_content()
    with tempfile.TemporaryDirectory(prefix="zhenbunandu-autoplay-") as temp_dir:
        game = GameSession(db=GameDB(Path(temp_dir) / "game.db"), content=loaded_content)
        game.new_game()
        seed_profile = apply_seed_scenario(game, seed)
        steps: list[dict[str, Any]] = [snapshot_state(game.state())]
        action_counts: Counter[str] = Counter()
        turn_actions: list[dict[str, Any]] = []

        while int(game.state()["game"]["turn"]) <= max_turns and not int(game.state()["game"]["ended"]):
            turn = int(game.state()["game"]["turn"])
            actions = play_strategy_turn(game, strategy, rng)
            for action in actions:
                action_counts[action.split(":")[0]] += 1
            result = game.resolve_turn()
            turn_actions.append(
                {
                    "turn": turn,
                    "actions": actions,
                    "timeline": result.get("timeline", []),
                    "warnings": result["state"]["reports"][0]["warnings"] if result["state"]["reports"] else [],
                }
            )
            steps.append(snapshot_state(result["state"]))

        final_state = game.state()
        final = snapshot_state(final_state)
        ending = final["ending"] or "未结束"
        run = {
            "strategy": strategy,
            "strategy_label": STRATEGY_LABELS.get(strategy, strategy),
            "seed": seed,
            "seed_profile": seed_profile,
            "max_turns": max_turns,
            "turn_count": len(turn_actions),
            "ended": final["ended"],
            "ending": ending,
            "final": final,
            "steps": steps,
            "turn_actions": turn_actions,
            "action_counts": dict(action_counts),
        }
        run["anomalies"] = detect_anomalies(run)
        return run


def summarize_runs(runs: list[dict[str, Any]]) -> dict[str, Any]:
    ending_counts = Counter(run["ending"] for run in runs)
    anomaly_counts = Counter(anomaly for run in runs for anomaly in run["anomalies"])
    action_counts = Counter(action for run in runs for action, count in run["action_counts"].items() for _ in range(count))
    by_strategy: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for run in runs:
        by_strategy[run["strategy"]].append(run)

    strategy_rows = []
    for strategy, items in sorted(by_strategy.items()):
        count = len(items)
        final = [item["final"] for item in items]
        strategy_action_counts = Counter(
            action for item in items for action, action_count in item["action_counts"].items() for _ in range(action_count)
        )
        strategy_rows.append(
            {
                "strategy": strategy,
                "label": STRATEGY_LABELS.get(strategy, strategy),
                "runs": count,
                "ended": sum(1 for item in items if item["ended"]),
                "avg_turns": round(sum(item["turn_count"] for item in items) / count, 1),
                "avg_treasury": round(sum(item["treasury"] for item in final) / count, 1),
                "avg_grain": round(sum(item["grain"] for item in final) / count, 1),
                "avg_city_defense": round(sum(item["city_defense"] for item in final) / count, 1),
                "avg_jin_pressure": round(sum(item["jin_pressure"] for item in final) / count, 1),
                "avg_peace_pressure": round(sum(item["peace_pressure"] for item in final) / count, 1),
                "avg_qinwang_response": round(sum(item["qinwang_response"] for item in final) / count, 1),
                "top_actions": dict(strategy_action_counts.most_common(5)),
                "anomalies": sum(len(item["anomalies"]) for item in items),
            }
        )

    total_runs = len(runs)
    return {
        "total_runs": total_runs,
        "ending_counts": dict(ending_counts),
        "anomaly_counts": dict(anomaly_counts),
        "action_counts": dict(action_counts.most_common(12)),
        "avg_turns": round(sum(run["turn_count"] for run in runs) / max(1, total_runs), 1),
        "early_collapse_rate": round(
            sum(1 for run in runs if "early-collapse" in run["anomalies"]) / max(1, total_runs),
            3,
        ),
        "strategy_rows": strategy_rows,
    }


def run_autoplay_batch(
    *,
    strategies: list[str] | None = None,
    seeds: list[str] | None = None,
    max_turns: int = 5,
    output_dir: Path | None = None,
) -> dict[str, Any]:
    selected_strategies = strategies or DEFAULT_STRATEGIES
    selected_seeds = seeds or DEFAULT_SEEDS
    content = load_content()
    runs = [
        run_single_autoplay(strategy, seed, max_turns=max_turns, content=content)
        for strategy in selected_strategies
        for seed in selected_seeds
    ]
    result = {"runs": runs, "summary": summarize_runs(runs)}
    if output_dir:
        write_autoplay_report(output_dir, result)
    return result


def write_autoplay_report(output_dir: Path, result: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "sample_turns").mkdir(exist_ok=True)
    runs = result["runs"]
    summary = result["summary"]

    (output_dir / "endings.json").write_text(
        json.dumps(summary["ending_counts"], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    with (output_dir / "metrics.csv").open("w", encoding="utf-8", newline="") as file:
        fieldnames = [
            "strategy",
            "seed",
            "turn",
            "treasury",
            "grain",
            "public_support",
            "authority",
            "city_defense",
            "defender_will",
            "jin_pressure",
            "peace_pressure",
            "grain_price",
            "qinwang_response",
            "max_faction_clock",
            "max_route_risk",
        ]
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for run in runs:
            for step in run["steps"]:
                writer.writerow({key: run.get(key) or step.get(key) for key in fieldnames})

    summary_lines = [
        "# 自动跑局摘要",
        "",
        f"- 总局数：{summary['total_runs']}",
        f"- 平均回合数：{summary['avg_turns']}",
        f"- 早崩率：{summary['early_collapse_rate']:.1%}",
        f"- 异常类型：{json.dumps(summary['anomaly_counts'], ensure_ascii=False)}",
        f"- 高频行动：{json.dumps(summary['action_counts'], ensure_ascii=False)}",
        "",
        "## 结局分布",
        "",
    ]
    summary_lines.extend(f"- {ending}：{count}" for ending, count in summary["ending_counts"].items())
    summary_lines.extend(["", "## 策略概览", ""])
    for row in summary["strategy_rows"]:
        top_actions = "、".join(f"{action}×{count}" for action, count in row["top_actions"].items()) or "无"
        summary_lines.append(
            f"- {row['label']}：{row['runs']} 局，均 {row['avg_turns']} 回合，城防均值 {row['avg_city_defense']}，"
            f"金军威压均值 {row['avg_jin_pressure']}，勤王均值 {row['avg_qinwang_response']}，"
            f"异常 {row['anomalies']}，常用行动：{top_actions}"
        )
    (output_dir / "summary.md").write_text("\n".join(summary_lines) + "\n", encoding="utf-8")

    route_lines = [
        "# 路线对比",
        "",
        "| 路线 | 平均国库 | 平均粮 | 平均城防 | 平均主和 | 平均金军 | 常用行动 |",
        "| --- | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in summary["strategy_rows"]:
        top_actions = "、".join(f"{action}×{count}" for action, count in row["top_actions"].items()) or "无"
        route_lines.append(
            f"| {row['label']} | {row['avg_treasury']} | {row['avg_grain']} | "
            f"{row['avg_city_defense']} | {row['avg_peace_pressure']} | {row['avg_jin_pressure']} | {top_actions} |"
        )
    (output_dir / "route_compare.md").write_text("\n".join(route_lines) + "\n", encoding="utf-8")

    anomaly_lines = ["# 异常报告", ""]
    if summary["anomaly_counts"]:
        for run in runs:
            if run["anomalies"]:
                anomaly_lines.append(f"- {run['strategy_label']} / {run['seed']}：{', '.join(run['anomalies'])}")
    else:
        anomaly_lines.append("- 未发现自动规则覆盖的异常。")
    (output_dir / "anomaly_report.md").write_text("\n".join(anomaly_lines) + "\n", encoding="utf-8")

    for run in runs[: min(8, len(runs))]:
        sample_path = output_dir / "sample_turns" / f"{run['strategy']}-{run['seed']}.json"
        sample_path.write_text(json.dumps(run["turn_actions"], ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run deterministic autoplay balance checks.")
    parser.add_argument("--strategies", nargs="*", default=DEFAULT_STRATEGIES)
    parser.add_argument("--seeds", nargs="*", default=DEFAULT_SEEDS)
    parser.add_argument("--max-turns", type=int, default=5)
    parser.add_argument("--output", type=Path, default=Path("runs/balance/latest"))
    args = parser.parse_args()
    result = run_autoplay_batch(
        strategies=args.strategies,
        seeds=args.seeds,
        max_turns=args.max_turns,
        output_dir=args.output,
    )
    print(json.dumps(result["summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
