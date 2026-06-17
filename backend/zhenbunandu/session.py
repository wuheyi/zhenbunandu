from __future__ import annotations

import json
from typing import Any, Iterator

from .content import GameContent, load_content
from .db import GameDB, clamp
from .llm import DEFAULT_LLM_BASE_URL, DEFAULT_LLM_MODEL, LLMClient, LLMResult, normalize_llm_settings


MONTHS = ["正月", "二月", "三月", "四月", "五月", "六月", "七月", "八月", "九月", "十月", "十一月", "十二月"]


def parse_json_list(value: str) -> list[Any]:
    try:
        parsed = json.loads(value or "[]")
        return parsed if isinstance(parsed, list) else []
    except json.JSONDecodeError:
        return []


class GameSession:
    def __init__(self, db: GameDB | None = None, content: GameContent | None = None):
        self.content = content or load_content()
        self.db = db or GameDB()

    def new_game(self) -> dict[str, Any]:
        self.db.reset_seed(self.content)
        return self.state()

    def menu_status(self) -> dict[str, Any]:
        has_game = self.db.row("SELECT * FROM game_state WHERE id = 1") is not None
        llm = self.db.get_setting("llm", {})
        return {
            "has_main_db": has_game,
            "has_api_key": bool(llm.get("api_key")),
            "llm": {k: v for k, v in llm.items() if k != "api_key"} if llm else None,
            "active_scenario": {"id": "jingkang_1126", "name": "靖康元年正月"},
        }

    def save_llm(self, payload: dict[str, Any]) -> dict[str, Any]:
        current = self.db.get_setting("llm", {}) or {}
        normalized = normalize_llm_settings(
            {
                "base_url": payload.get("base_url", current.get("base_url", DEFAULT_LLM_BASE_URL)),
                "model": payload.get("model", current.get("model", DEFAULT_LLM_MODEL)),
                "api_key": payload.get("api_key", current.get("api_key", "")),
            }
        )
        value = normalized
        self.db.set_setting("llm", value)
        return self.menu_status()

    def _llm_client(self) -> LLMClient:
        return LLMClient(self.db.get_setting("llm", {}) or {})

    def _build_guidance(
        self,
        game: dict[str, Any],
        metrics: list[dict[str, Any]],
        siege: dict[str, Any],
        events: list[dict[str, Any]],
        directives: list[dict[str, Any]],
        cases: list[dict[str, Any]],
        routes: list[dict[str, Any]],
        clocks: list[dict[str, Any]],
    ) -> dict[str, Any]:
        metric_map = {item["key"]: int(item["value"]) for item in metrics}
        active_directives = [item for item in directives if item["status"] in {"draft", "confirmed"}]
        ready_cases = [item for item in cases if item["status"] == "ready"]
        active_events = [item for item in events if item["status"] == "active"]
        turn = int(game.get("turn", 1))
        tips: list[dict[str, str]] = []
        risk_flags: list[str] = []

        if int(game.get("ended", 0)):
            return {
                "stage": "复盘",
                "priority": "本局已结束，先看结局复盘和最近月末回奏。",
                "tips": [
                    {
                        "title": "查看失败原因",
                        "body": "回奏中会列出拖垮局势的关键链条，可据此调整下一局前三回合。",
                        "action": "打开月末回奏",
                        "target": "report",
                    }
                ],
                "risk_flags": [],
            }

        if turn == 1:
            stage = "初登大宝"
            priority = "先处理金军、禁军欠饷、李纲请守三件急务。"
            if not any("李纲" in item["title"] for item in active_directives):
                tips.append(
                    {
                        "title": "稳住宣化门",
                        "body": "召见李纲可生成守城草案，影响后续宣化门夜攻判定。",
                        "action": "召见李纲",
                        "target": "minister:li_gang",
                    }
                )
            if not any("急饷" in item["title"] or "内帑" in item["title"] for item in active_directives):
                tips.append(
                    {
                        "title": "先补禁军急饷",
                        "body": "欠饷会削弱守军战意，户部方案会把钱粮来源写入草案。",
                        "action": "召见户部",
                        "target": "minister:finance_minister",
                    }
                )
            if not any("军饷" in item["title"] for item in self.db.rows("SELECT title FROM secret_orders WHERE status = 'active'")):
                tips.append(
                    {
                        "title": "暗查东仓账册",
                        "body": "密令会在月末产出证据，为第二回合殿前对质埋下爽点。",
                        "action": "交付密令",
                        "target": "secret",
                    }
                )
        elif ready_cases:
            stage = "证据与对质"
            priority = "证据已到御前，适合开殿前对质形成清算反馈。"
            tips.append(
                {
                    "title": "开禁军欠饷案",
                    "body": "东仓副册可公开使用，裁断会影响国库、君威、禁军战意和财税派系反扑。",
                    "action": "开殿前对质",
                    "target": "court",
                }
            )
        else:
            stage = "围城筹备"
            priority = "用朝议把勤王、粮价、议和三条压力拆成可执行草案。"
            if int(siege.get("qinwang_response", 0)) < 40:
                tips.append(
                    {
                        "title": "催发勤王",
                        "body": "勤王响应偏低，陕西西军路线会继续迟滞，需赏格和粮草承诺。",
                        "action": "开朝议",
                        "target": "debate",
                    }
                )
            if int(siege.get("grain_price", 100)) >= 135 or metric_map.get("京城粮", 0) <= 24:
                tips.append(
                    {
                        "title": "压住京城粮价",
                        "body": "粮价会转化为民心与守军战意压力，可用开仓平粜或催江淮粮道处理。",
                        "action": "看粮运财税",
                        "target": "map:logistics:jianghuai",
                    }
                )
            if int(siege.get("jin_pressure", 0)) >= 68:
                tips.append(
                    {
                        "title": "准备夜攻检验",
                        "body": "金军威压已高，城门、器械、守军战意会共同影响战报结果。",
                        "action": "看汴京城防",
                        "target": "map:city:xuanhua_gate",
                    }
                )

        if not tips and active_events:
            event = active_events[0]
            tips.append(
                {
                    "title": event["title"],
                    "body": event["summary"],
                    "action": "查看急奏",
                    "target": f"event:{event['id']}",
                }
            )

        if int(siege.get("jin_pressure", 0)) >= 70:
            risk_flags.append("金军威压逼近强攻阈值。")
        if int(siege.get("peace_pressure", 0)) >= 65:
            risk_flags.append("主和压力过高，可能压低君威并触发屈辱和议。")
        if int(siege.get("gate_risk", 0)) >= 55:
            risk_flags.append("城门内应风险偏高，夜值与排查需要跟上。")
        if int(siege.get("grain_price", 100)) >= 160:
            risk_flags.append("粮价进入恐慌区，会持续伤民心和守军战意。")
        if metric_map.get("京城粮", 999) <= 18:
            risk_flags.append("京城粮储偏低，围城消耗会快速拖垮局势。")
        stalled_route = next((route for route in routes if int(route.get("risk", 0)) >= 55 or int(route.get("eta", 0)) >= 4), None)
        if stalled_route:
            risk_flags.append(f"{stalled_route['name']}迟滞，需查账、护粮或补赏格。")
        hot_clock = next((clock for clock in sorted(clocks, key=lambda item: int(item.get("value", 0)), reverse=True) if int(clock.get("stage", 0)) >= 2), None)
        if hot_clock:
            risk_flags.append(f"{hot_clock['title']}已成反扑链条，需在人物谱中缓和。")

        return {
            "stage": stage,
            "priority": priority,
            "tips": tips[:4],
            "risk_flags": risk_flags[:4],
        }

    def _build_postmortem(
        self,
        game: dict[str, Any],
        metrics: list[dict[str, Any]],
        siege: dict[str, Any],
        issues: list[dict[str, Any]],
        routes: list[dict[str, Any]],
    ) -> dict[str, Any]:
        if not int(game.get("ended", 0)):
            return {"status": "active", "reasons": [], "recommendations": []}

        metric_map = {item["key"]: int(item["value"]) for item in metrics}
        issue_map = {item["id"]: int(item["value"]) for item in issues}
        reasons: list[str] = []
        recommendations: list[str] = []

        if int(siege.get("city_defense", 0)) <= 35 or issue_map.get("defend_bianjing", 0) < -25:
            reasons.append("汴京守备长期不足，城墙、器械或守将没有形成合力。")
            recommendations.append("第一回合优先召见李纲，明确承办人与工部、殿前司资源。")
        if int(siege.get("defender_will", 0)) <= 40 or issue_map.get("discipline_guards", 0) < -25:
            reasons.append("禁军欠饷和军纪拖低守军战意。")
            recommendations.append("补发急饷要和核验营册、密查账册一起做，避免只申饬不补钱。")
        if int(siege.get("peace_pressure", 0)) >= 70 or metric_map.get("君威", 100) <= 40:
            reasons.append("主和压力压过君威，朝堂开始绕开圣断。")
            recommendations.append("议和可以拖时间，但同时要修城、催勤王，并守住割地质子底线。")
        if int(siege.get("qinwang_response", 0)) <= 35 or issue_map.get("qinwang_call", 0) < -35:
            reasons.append("勤王响应不足，汴京缺少外部解围希望。")
            recommendations.append("发勤王诏时写清赏格、军粮来源和接应路线。")
        if int(siege.get("grain_price", 100)) >= 165 or metric_map.get("京城粮", 999) <= 16:
            reasons.append("粮价与粮储恶化，民心和守城耐力被持续消耗。")
            recommendations.append("尽早开仓平粜，同时催江淮粮道，避免只消耗京城存粮。")
        route = next((item for item in routes if item["id"] == "jianghuai_grain_to_bianjing"), None)
        if route and int(route.get("risk", 0)) >= 58:
            reasons.append("江淮粮道风险过高，粮船迟滞没有被及时处理。")
            recommendations.append("用查账、护粮、提高运费或改道降低粮运风险。")

        if not reasons:
            reasons.append("本局并非单点崩盘，而是金军、粮价、勤王和朝堂压力叠加。")
        if not recommendations:
            recommendations.append("下一局前三回合保持守城、补饷、密查、勤王四条线并行。")

        return {
            "status": "ended",
            "ending": game.get("ending", ""),
            "reasons": reasons[:5],
            "recommendations": recommendations[:5],
        }

    def _diplomacy_demand_text(self, severity: int) -> str:
        if severity >= 75:
            return "索三镇、质子入营、罢李纲，并开城犒军"
        if severity >= 60:
            return "索犒军金银、质子入营，并请罢李纲以示诚意"
        if severity >= 45:
            return "索犒军金银、岁币加码，并限期复命"
        return "金营条件暂缓，仅催犒军与使节往还"

    def _build_diplomacy_options(
        self,
        diplomacy: dict[str, Any],
        metrics: list[dict[str, Any]],
        siege: dict[str, Any],
        terms: list[dict[str, Any]] | None = None,
        incidents: list[dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        metric_map = {item["key"]: int(item["value"]) for item in metrics}
        severity = int(diplomacy.get("demand_severity", 0))
        leverage = int(diplomacy.get("leverage", 0))
        defense_total = int(siege.get("city_defense", 0)) + int(siege.get("defender_will", 0)) + leverage
        active_term = next((term for term in terms or [] if term["status"] == "active"), None)
        active_incident = next((incident for incident in incidents or [] if incident["status"] == "active"), None)

        def option(
            action: str,
            title: str,
            intent: str,
            cost: str,
            benefit: str,
            risk: str,
            effects: list[str],
            available: bool = True,
            disabled_reason: str = "",
        ) -> dict[str, Any]:
            return {
                "action": action,
                "title": title,
                "intent": intent,
                "cost": cost,
                "benefit": benefit,
                "risk": risk,
                "effects": effects,
                "available": available,
                "disabled_reason": disabled_reason,
            }

        options = [
            option(
                "stall",
                "假议和拖延",
                "用复命、礼物和模糊文字买修城与勤王时间。",
                "国库 3，君威小降",
                "急躁下降，金军威压暂缓，宋方筹码微升",
                "主和压力和南迁暗议会上升，拖久会被识破",
                ["金军威压 -5", "急躁 -13", "主和压力 +6", "宋方筹码 +3"],
            ),
            option(
                "tribute",
                "犒军纳赂",
                "先给一笔犒军金银，换取攻城节奏放慢。",
                "国库 8，君威下降",
                "条件和急躁下降，金军威压下降明显",
                "金营会把让步视为软弱，主和派借势抬头",
                ["国库 -8", "条件 -8", "急躁 -12", "金军威压 -8"],
                available=metric_map.get("国库", 0) >= 4,
                disabled_reason="国库几近空竭，已拿不出可见犒军银。",
            ),
            option(
                "hardline",
                "强硬拒使",
                "公开拒绝苛索，逼朝堂和禁军承认只能守城。",
                "金军急躁上升",
                "君威、战意和谈判筹码上升，主和压力下降",
                "城防和勤王未成时，可能提前激怒金军",
                [
                    "君威 +4",
                    "守军战意 +5",
                    "主和压力 -5",
                    "金军威压 +7" if defense_total < 125 else "金军威压 +3",
                ],
            ),
            option(
                "divide",
                "分化金营",
                "密支收买金营部族与使者，让其争功互疑。",
                "内帑 4，信任下降",
                "金营内讧和宋方筹码上升，急躁下降",
                "需要秘密花费；若后续失信，金军条件会更苛",
                ["内帑 -4", "金营内讧 +16", "宋方筹码 +8", "急躁 -6"],
                available=metric_map.get("内帑", 0) >= 4,
                disabled_reason="内帑不足，皇城司无钱收买金营暗线。",
            ),
            option(
                "refuse_terms",
                "拒割地质子",
                "把割地、质子划为底线，但保留犒军与岁币的谈判余地。",
                "金方信任下降",
                "君威和守军战意上升，主和压力下降",
                "条件严重度会上升；若筹码不足，金军威压也会上升",
                ["君威 +6", "主和压力 -7", "条件 +5", "宋方筹码 +5"],
                available=severity >= 55,
                disabled_reason="金营尚未正式抛出割地质子底线。",
            ),
        ]
        if active_term:
            cost = "内帑 2" if active_term["kind"] == "divide" else "国库 4"
            available_money = metric_map.get("内帑" if active_term["kind"] == "divide" else "国库", 0)
            options.insert(
                0,
                option(
                    "honor_terms",
                    "履约安抚",
                    f"按“{active_term['title']}”补足使费、回书或暗线承诺，避免金营以失信再犯。",
                    cost,
                    "履约度上升，失信风险下降，金方急躁小降",
                    "继续付出钱粮会滋长主和压力，且不能解决守城本身",
                    ["履约 +25", "失信风险 -20", "急躁 -5", "宋方筹码 +2"],
                    available=available_money >= (2 if active_term["kind"] == "divide" else 4),
                    disabled_reason="钱粮不足，暂时无法补足条款承诺。",
                ),
            )
        if active_incident:
            options.insert(
                0,
                option(
                    "redeem_envoy",
                    "赎回使节",
                    f"按金营留难“{active_incident['envoy_name']}”一事补给犒军尾款，换回使节与草约副本。",
                    "国库 5，君威小降",
                    "扣使烈度下降，金方信任回升，急躁下降",
                    "主和派会借机鼓吹真和，且开了再索金银的口子",
                    ["国库 -5", "扣使 -35", "信任 +6", "急躁 -8"],
                    available=metric_map.get("国库", 0) >= 5,
                    disabled_reason="国库不足，拿不出赎使与犒军尾款。",
                ),
            )
            options.insert(
                1,
                option(
                    "extract_envoy",
                    "密取使节",
                    f"让皇城司借金营内讧暗线接出“{active_incident['envoy_name']}”。",
                    "内帑 3，信任下降",
                    "扣使烈度下降，金营内讧上升，宋方筹码增加",
                    "若走漏，金营会把密取视作背约，后续索约更硬",
                    ["内帑 -3", "扣使 -25", "内讧 +8", "筹码 +5"],
                    available=metric_map.get("内帑", 0) >= 3,
                    disabled_reason="内帑不足，皇城司无法打通金营暗线。",
                ),
            )
            options.insert(
                2,
                option(
                    "abandon_envoy",
                    "弃使明底线",
                    "公开承认使节受辱也不许割地质子，把谈判焦点转回守城。",
                    "金军威压上升",
                    "君威和守军战意上升，主和压力下降",
                    "使节难返，金营急躁与条件都会上升",
                    ["君威 +5", "守军战意 +4", "急躁 +8", "金军威压 +6"],
                ),
            )
        return options

    def test_llm(self) -> dict[str, Any]:
        client = self._llm_client()
        fallback = "未配置 API key；当前将使用确定性规则结算。"
        result = client.complete(
            [
                {
                    "role": "system",
                    "content": "你是《朕不南渡》的本地连通性测试。只用一句古雅但清楚的中文回答。",
                },
                {"role": "user", "content": "回一句：御案已通，仍守汴京。"},
            ],
            fallback=fallback,
            temperature=0.2,
            max_tokens=80,
        )
        return {
            "ok": result.used_llm,
            "configured": client.configured,
            "used_llm": result.used_llm,
            "model": client.model,
            "base_url": client.base_url,
            "sample": result.text,
            "error": result.error,
        }

    def _polish_minister_answer(self, minister: dict[str, Any], user_message: str, deterministic_answer: str) -> LLMResult:
        client = self._llm_client()
        return client.complete(
            [
                {
                    "role": "system",
                    "content": (
                        "你是历史政略游戏《朕不南渡》的大臣奏对润色器。"
                        "必须保留事实、行动建议、金额、期限、风险，不得新增草案、证据、数值收益或结局。"
                        "口吻为北宋朝堂奏对，中文，120-180字。"
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"人物：{minister['name']}，官职：{minister['office']}，立场：{minister['stance']}。\n"
                        f"皇帝追问：{user_message or '本月急务如何处置？'}\n"
                        f"规则层给出的确定性回答：{deterministic_answer}\n"
                        "请润色为更有角色感的奏对。"
                    ),
                },
            ],
            fallback=deterministic_answer,
            temperature=0.55,
            max_tokens=260,
        )

    def _polish_report_summary(
        self,
        summary: str,
        timeline: list[str],
        directive_results: list[dict[str, str]],
        warnings: list[str],
    ) -> LLMResult:
        client = self._llm_client()
        return client.complete(
            [
                {
                    "role": "system",
                    "content": (
                        "你是《朕不南渡》的月末回奏润色器。"
                        "只改写总评一句，不得改变任何事实、数值、顺序、人物或警告。"
                        "输出一段中文，80-130字。"
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"确定性总评：{summary}\n"
                        f"时间线：{json.dumps(timeline, ensure_ascii=False)}\n"
                        f"诏令结果：{json.dumps(directive_results, ensure_ascii=False)}\n"
                        f"下月预警：{json.dumps(warnings, ensure_ascii=False)}\n"
                        "请润色总评。"
                    ),
                },
            ],
            fallback=summary,
            temperature=0.45,
            max_tokens=220,
        )

    def state(self) -> dict[str, Any]:
        if not self.db.row("SELECT * FROM game_state WHERE id = 1"):
            self.new_game()
        if not self.db.row("SELECT id FROM faction_clocks LIMIT 1"):
            self.db.seed_faction_clocks()
        if not self.db.row("SELECT id FROM route_nodes LIMIT 1"):
            self.db.seed_route_nodes(self.content.route_nodes)
        game = self.db.row("SELECT * FROM game_state WHERE id = 1") or {}
        metrics = self.db.rows("SELECT key, value, last_delta FROM metrics ORDER BY rowid")
        siege = self.db.row("SELECT * FROM siege_state WHERE id = 1") or {}
        events = self.db.rows("SELECT * FROM events ORDER BY urgency DESC, severity DESC")
        for event in events:
            event["interests"] = parse_json_list(event["interests"])
            event["audiences"] = parse_json_list(event["audiences"])
            event["actions"] = parse_json_list(event["actions"])
        orders = self.db.rows("SELECT * FROM secret_orders ORDER BY id DESC")
        for order in orders:
            order["tags"] = parse_json_list(order["tags"])
        evidence = self.db.rows("SELECT * FROM evidence_items ORDER BY created_turn DESC, strength DESC")
        for item in evidence:
            item["implicated"] = parse_json_list(item["implicated"])
            item["usable_in_court"] = bool(item["usable_in_court"])
        cases = self.db.rows("SELECT * FROM court_cases ORDER BY created_turn DESC")
        for case in cases:
            case["suspects"] = parse_json_list(case["suspects"])
            case["evidence_ids"] = parse_json_list(case["evidence_ids"])
        reports = self.db.rows("SELECT * FROM turn_reports ORDER BY id DESC LIMIT 6")
        for report in reports:
            report["metrics_delta"] = json.loads(report.pop("metrics_delta_json") or "{}")
            report["timeline"] = json.loads(report.pop("timeline_json") or "[]")
            report["directives"] = json.loads(report.pop("directives_json") or "[]")
            report["warnings"] = json.loads(report.pop("warnings_json") or "[]")
        battles = self.db.rows("SELECT * FROM battle_reports ORDER BY id DESC LIMIT 6")
        for battle in battles:
            battle["reasons"] = json.loads(battle.pop("reasons_json") or "[]")
            battle["losses"] = json.loads(battle.pop("losses_json") or "{}")
            battle["changes"] = json.loads(battle.pop("changes_json") or "{}")
        debates = self.db.rows("SELECT * FROM court_debates ORDER BY id DESC LIMIT 4")
        for debate in debates:
            debate["options"] = json.loads(debate.pop("options_json") or "[]")
            debate["speakers"] = json.loads(debate.pop("speakers_json") or "[]")
        directives = self.db.rows("SELECT * FROM directives ORDER BY id")
        issues = self.db.rows("SELECT * FROM issues ORDER BY rowid")
        routes = self.db.rows("SELECT * FROM logistics_routes ORDER BY rowid")
        route_nodes = self.db.rows("SELECT * FROM route_nodes ORDER BY route_id, rowid")
        nodes_by_route: dict[str, list[dict[str, Any]]] = {}
        for node in route_nodes:
            nodes_by_route.setdefault(node["route_id"], []).append(node)
        for route in routes:
            nodes = nodes_by_route.get(route["id"], [])
            route["nodes"] = nodes
            credit_nodes = [node for node in nodes if node["kind"] in {"market", "collection"}]
            route["merchant_credit"] = min((int(node["progress"]) for node in credit_nodes), default=60)
            route["blocked_nodes"] = sum(1 for node in nodes if int(node["risk"]) >= 55)
        clocks = self.db.rows("SELECT * FROM faction_clocks ORDER BY value DESC, rowid")
        diplomacy = self.db.row("SELECT * FROM diplomacy_state WHERE id = 1") or {}
        diplomacy_terms = self.db.rows(
            "SELECT * FROM diplomacy_terms ORDER BY CASE status WHEN 'active' THEN 0 ELSE 1 END, due_turn, id"
        )
        diplomacy_incidents = self.db.rows(
            "SELECT * FROM diplomacy_incidents ORDER BY CASE status WHEN 'active' THEN 0 ELSE 1 END, deadline_turn, id"
        )
        guidance = self._build_guidance(game, metrics, siege, events, directives, cases, routes, clocks)
        postmortem = self._build_postmortem(game, metrics, siege, issues, routes)
        return {
            "game": game,
            "metrics": metrics,
            "siege": siege,
            "diplomacy": diplomacy,
            "diplomacy_terms": diplomacy_terms,
            "diplomacy_incidents": diplomacy_incidents,
            "diplomacy_options": self._build_diplomacy_options(diplomacy, metrics, siege, diplomacy_terms, diplomacy_incidents),
            "events": events,
            "issues": issues,
            "ministers": self.db.rows("SELECT * FROM characters ORDER BY rowid"),
            "factions": self.db.rows("SELECT * FROM factions ORDER BY rowid"),
            "faction_clocks": clocks,
            "regions": self.db.rows("SELECT * FROM regions ORDER BY rowid"),
            "armies": self.db.rows("SELECT * FROM armies ORDER BY rowid"),
            "gates": self.db.rows("SELECT * FROM city_gates ORDER BY rowid"),
            "logistics_routes": routes,
            "directives": directives,
            "secret_orders": orders,
            "evidence": evidence,
            "court_cases": cases,
            "reports": reports,
            "battle_reports": battles,
            "court_debates": debates,
            "ledger": self.db.rows("SELECT * FROM economy_ledger ORDER BY id DESC LIMIT 12"),
            "memories": self.db.rows("SELECT * FROM memories ORDER BY id DESC LIMIT 12"),
            "llm_configured": bool((self.db.get_setting("llm", {}) or {}).get("api_key")),
            "directive_templates": self.content.directive_templates,
            "guidance": guidance,
            "postmortem": postmortem,
        }

    def minister_chat(self, minister_id: str, message: str = "") -> dict[str, Any]:
        minister = self.db.row("SELECT * FROM characters WHERE id = ?", (minister_id,))
        if not minister:
            raise KeyError("未找到此人。")
        created_directive: dict[str, Any] | None = None
        created_order: dict[str, Any] | None = None
        answer = "臣谨听圣问。此事宜先定承办、钱粮和期限，再下明旨。"
        if minister_id == "li_gang":
            answer = "臣李纲以为，宣化门乃北面要冲。若陛下许臣临督城防，明示工部、开封府、殿前司听调，本月即可先稳一门。"
            created_directive = self.db.create_directive(
                {
                    "title": "任李纲临督宣化门城防",
                    "text": "任李纲临督宣化门城防，节制工部、开封府与殿前司相关守备，三日内修补城楼、备炮石火油、核夜值。",
                    "form": "任命诏",
                    "domain": "军事",
                    "target": "宣化门",
                    "assignee": "李纲",
                    "resources": "工部料物、殿前司守军、开封府民壮",
                    "deadline": "本月",
                    "risk": "主和宰执弹劾专权，民夫征发伤民心",
                }
            )
        elif minister_id == "finance_minister":
            answer = "国库虚，却不能任禁军三月无饷。臣请以内帑五万贯、国库八万贯先补殿前司急饷，另命开封府核验营册，免再被层层截留。"
            created_directive = self.db.create_directive(
                {
                    "title": "开内帑补禁军急饷",
                    "text": "以内帑五万贯、国库八万贯补发殿前司禁军急饷，户部拨款，开封府核验营册，月底具数回奏。",
                    "form": "拨款诏",
                    "domain": "财政",
                    "target": "殿前司禁军",
                    "assignee": "户部尚书",
                    "resources": "内帑五万贯、国库八万贯",
                    "deadline": "本月",
                    "risk": "库空、转运截留、宗室内廷不满",
                }
            )
        elif minister_id == "imperial_city司":
            answer = "臣可令暗线夜查东仓副册，先不惊动户部。若拨付数与实发数相左，便可为殿前对质之证。"
            created_order = self.db.create_secret_order(
                {
                    "title": "密查禁军军饷账册",
                    "assignee": "皇城司使",
                    "content": "三日内核验户部军饷拨付、东仓出入与殿前司实发账册，勿惊动转运判官。",
                    "tags": ["禁军欠饷", "东仓", "转运财税网络"],
                    "secrecy": 78,
                    "risk": 36,
                }
            )
        elif minister_id == "peace_chancellor":
            answer = "臣非不知守城之义，只恐金军压境而粮饷不继。议和可买一月，然割地、质子诸议万不可轻许。"
            created_directive = self.db.create_directive(
                {
                    "title": "遣使假议和拖延金军",
                    "text": "遣使入金营，只许犒军与岁币议程，严禁割地质子；以三日一复命拖延攻城，同时暗催勤王与修城。",
                    "form": "国书",
                    "domain": "外交",
                    "target": "金军东路",
                    "assignee": "主和宰执",
                    "resources": "犒军银三万贯、外交礼物",
                    "deadline": "三日内",
                    "risk": "主战清议不满，若被识破金军将更强硬",
                }
            )
        elif minister_id == "kaifeng_prefect":
            answer = "臣可查粮价、核营册、征民壮，但若无钱粮明旨，开封府只会在百姓与禁军之间两头受怨。"
            created_directive = self.db.create_directive(
                {
                    "title": "开仓平粜稳京城粮价",
                    "text": "命开封府会同户部开常平仓五万石平粜，严禁豪右囤积，坊市不得借兵事哄抬米价。",
                    "form": "榜文",
                    "domain": "民政",
                    "target": "京城粮价",
                    "assignee": "开封府尹",
                    "resources": "京城粮五万石、开封府吏役",
                    "deadline": "十日内",
                    "risk": "粮储下降，商户粮行可能闭市观望",
                }
            )
        elif minister_id == "guard_representative":
            answer = "臣愿守城，但军中最怕只严军纪不发钱粮。若陛下明定换防、夜值与犒赏，禁军尚可一战。"
            created_directive = self.db.create_directive(
                {
                    "title": "整肃城门夜值与禁军军纪",
                    "text": "命殿前司重排宣化门、新宋门夜值，赏守夜弩手，严禁军士聚饮鼓噪，开封府协查城门内应。",
                    "form": "军令",
                    "domain": "军事",
                    "target": "宣化门与新宋门",
                    "assignee": "禁军都虞候",
                    "resources": "军赏二万贯、开封府巡检",
                    "deadline": "三日内",
                    "risk": "只罚不赏将激起军中怨气",
                }
            )
        llm_result = self._polish_minister_answer(minister, message, answer)
        answer = llm_result.text
        return {
            "minister": minister,
            "answer": answer,
            "proposed_directive": created_directive,
            "secret_order": created_order,
            "llm": {"used": llm_result.used_llm, "error": llm_result.error},
            "state": self.state(),
        }

    def create_secret_order(self, payload: dict[str, Any]) -> dict[str, Any]:
        title = str(payload.get("title") or "密查禁军军饷账册")
        order = self.db.create_secret_order(
            {
                "title": title,
                "assignee": payload.get("assignee") or "皇城司使",
                "content": payload.get("content") or title,
                "tags": payload.get("tags") or ["禁军欠饷", "账册"],
                "secrecy": payload.get("secrecy", 72),
                "risk": payload.get("risk", 34),
            }
        )
        return {"order": order, "orders": self.state()["secret_orders"]}

    def create_directive(self, payload: dict[str, Any]) -> dict[str, Any]:
        title = str(payload.get("title") or payload.get("text") or "临机诏令")[:40]
        directive = self.db.create_directive(
            {
                "title": title,
                "text": payload.get("text") or title,
                "form": payload.get("form", "圣旨"),
                "domain": payload.get("domain", "军政"),
                "target": payload.get("target", "当前急务"),
                "assignee": payload.get("assignee", "中书门下"),
                "resources": payload.get("resources", "依实拨付"),
                "deadline": payload.get("deadline", "本月"),
                "risk": payload.get("risk", "执行偏差"),
            }
        )
        return {"directive": directive, "directives": self.state()["directives"]}

    def create_debate(self, topic: str = "战和与勤王") -> dict[str, Any]:
        state = self.db.row("SELECT * FROM game_state WHERE id = 1") or {"turn": 1}
        turn = int(state["turn"])
        existing = self.db.row(
            "SELECT * FROM court_debates WHERE turn = ? AND topic = ? ORDER BY id DESC LIMIT 1",
            (turn, topic),
        )
        if existing:
            return {"debate": self.state()["court_debates"][0], "state": self.state()}
        speakers = [
            {"name": "李纲", "stance": "主战", "line": "议和只可买时日，不可撤城防；请先固宣化门，再催西军。"},
            {"name": "主和宰执", "stance": "主和", "line": "金军锐甚，若一味拒使，城中粮价与宗室恐惧皆会化作内乱。"},
            {"name": "户部尚书", "stance": "财赋", "line": "发勤王诏必须配赏格，开仓平粜也要说明粮从何处补回。"},
            {"name": "开封府尹", "stance": "京城", "line": "民心未散，但粮价再涨，坊市先乱于敌骑之前。"},
        ]
        options = [
            {
                "title": "假议和拖延",
                "benefit": "金军威压短降，争取修城和勤王时间。",
                "cost": "君威和主战清议受损，失信后金营更强硬。",
            },
            {
                "title": "催发勤王",
                "benefit": "提升西军入援概率，河东屏障不至孤立。",
                "cost": "需要赏格和粮草，否则地方只会观望。",
            },
            {
                "title": "开仓平粜",
                "benefit": "粮价压力下降，民心与守城战意稍稳。",
                "cost": "京城粮储下降，商户粮行可能反弹。",
            },
        ]
        with self.db.conn:
            cur = self.db.conn.execute(
                """INSERT INTO court_debates
                   (turn, topic, summary, options_json, speakers_json, status)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    turn,
                    topic,
                    "朝议未给出唯一答案，却把战和、勤王、粮价三条压力摆到御案上。",
                    json.dumps(options, ensure_ascii=False),
                    json.dumps(speakers, ensure_ascii=False),
                    "completed",
                ),
            )
            self.db.create_directive(
                {
                    "title": "发勤王诏催西军入援",
                    "text": "遣中使持手诏赴陕西路，命种师道整西军东援，许到汴后优先补饷，并令河东诸军牵制金军西路。",
                    "form": "手诏",
                    "domain": "军事",
                    "target": "陕西西军与河东诸军",
                    "assignee": "中书门下",
                    "resources": "赏格六万贯、军粮八万石承诺",
                    "deadline": "本月启程",
                    "risk": "赏格若不到位，西军怨望反增",
                }
            )
            self.db.create_directive(
                {
                    "title": "遣使假议和拖延金军",
                    "text": "遣使入金营，只许犒军与岁币议程，严禁割地质子；以三日一复命拖延攻城，同时暗催勤王与修城。",
                    "form": "国书",
                    "domain": "外交",
                    "target": "金军东路",
                    "assignee": "主和宰执",
                    "resources": "犒军银三万贯、外交礼物",
                    "deadline": "三日内",
                    "risk": "主战清议不满，若被识破金军将更强硬",
                }
            )
            self.db.create_directive(
                {
                    "title": "开仓平粜稳京城粮价",
                    "text": "命开封府会同户部开常平仓五万石平粜，严禁豪右囤积，坊市不得借兵事哄抬米价。",
                    "form": "榜文",
                    "domain": "民政",
                    "target": "京城粮价",
                    "assignee": "开封府尹",
                    "resources": "京城粮五万石、开封府吏役",
                    "deadline": "十日内",
                    "risk": "粮储下降，商户粮行可能闭市观望",
                }
            )
        debate = self.db.row("SELECT * FROM court_debates WHERE id = ?", (cur.lastrowid,))
        return {"debate": debate, "state": self.state()}

    def patch_directive(self, directive_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        current = self.db.row("SELECT * FROM directives WHERE id = ?", (directive_id,))
        if not current:
            raise KeyError("未找到诏令。")
        fields = ["title", "text", "form", "domain", "target", "assignee", "resources", "deadline", "risk", "status"]
        updates = {field: payload[field] for field in fields if field in payload}
        if updates:
            parts = ", ".join(f"{field} = ?" for field in updates)
            self.db.conn.execute(f"UPDATE directives SET {parts} WHERE id = ?", [*updates.values(), directive_id])
            self.db.conn.commit()
        return {"directive": self.db.row("SELECT * FROM directives WHERE id = ?", (directive_id,)), "directives": self.state()["directives"]}

    def confirm_directive(self, directive_id: int) -> dict[str, Any]:
        self.db.conn.execute("UPDATE directives SET status = 'confirmed' WHERE id = ?", (directive_id,))
        self.db.conn.commit()
        return {"directives": self.state()["directives"]}

    def _complete_secret_orders(self, turn: int, timeline: list[str]) -> None:
        active = self.db.rows("SELECT * FROM secret_orders WHERE status = 'active'")
        for order in active:
            if "军饷" not in order["title"] and "账册" not in order["content"]:
                continue
            result = "皇城司夜入东仓，得副册一卷：户部拨付与殿前司实发数不合，中间经转运判官手。"
            self.db.conn.execute(
                "UPDATE secret_orders SET status = 'done', progress = 100, result = ? WHERE id = ?",
                (result, order["id"]),
            )
            self.db.ensure_evidence_and_case(turn + 1)
            timeline.append("皇城司密查得东仓副册，禁军欠饷案可开殿前对质。")

    def _schedule_historical_anchors(self, next_turn: int) -> None:
        for anchor in self.content.historical_anchors:
            if int(anchor.get("turn", 0)) != next_turn:
                continue
            self.db.upsert_event({**anchor, "status": "active", "read": 0, "focus": 1})
            if anchor["id"] == "turn2_jin_envoy":
                self.db.set_diplomacy_text(
                    current_demand="索犒军金银、质子入营，并请罢李纲以示诚意",
                    status="金使入城",
                )
                self.db.change_diplomacy("demand_severity", 10)
                self.db.change_diplomacy("impatience", 6)

    def _resolve_night_attack(
        self,
        turn: int,
        metric_deltas: dict[str, int],
        siege_deltas: dict[str, int],
        timeline: list[str],
    ) -> None:
        if turn < 2 or self.db.row("SELECT id FROM battle_reports WHERE title = '宣化门夜攻'"):
            return
        siege = self.db.row("SELECT * FROM siege_state WHERE id = 1") or {}
        gate = self.db.row("SELECT * FROM city_gates WHERE id = 'xuanhua_gate'") or {}
        city_defense = int(siege.get("city_defense", 0)) + siege_deltas.get("city_defense", 0)
        defender_will = int(siege.get("defender_will", 0)) + siege_deltas.get("defender_will", 0)
        jin_pressure = int(siege.get("jin_pressure", 0)) + siege_deltas.get("jin_pressure", 0)
        gate_risk = int(siege.get("gate_risk", 0)) + siege_deltas.get("gate_risk", 0)
        gate_condition = int(gate.get("condition", 0))
        gate_equipment = int(gate.get("equipment", 0))
        li_gang_bonus = 12 if gate.get("commander") == "李纲" else 0
        score = city_defense + defender_will + gate_condition + gate_equipment + li_gang_bonus - jin_pressure - gate_risk
        reasons = [
            f"城防 {city_defense}",
            f"守军战意 {defender_will}",
            f"宣化门坚固 {gate_condition}",
            f"器械 {gate_equipment}",
        ]
        if li_gang_bonus:
            reasons.append("李纲临城督战")
        if score >= 105:
            outcome = "小胜"
            summary = "金军夜攻宣化门，李纲预置火油与炮石，禁军虽有惊动仍能据城还击，三鼓后敌军退。"
            changes = {"city_defense": -2, "defender_will": 8, "jin_pressure": -8, "peace_pressure": -5, "qinwang_response": 5}
            metric_deltas["君威"] = metric_deltas.get("君威", 0) + 5
            self.db.change_issue("defend_bianjing", 12)
            self.db.change_issue("qinwang_call", 6)
        elif score >= 75:
            outcome = "相持"
            summary = "金军夜探城壕，宣化门守军鏖战至晓，城楼小损，敌军亦未能登城。"
            changes = {"city_defense": -5, "defender_will": 1, "jin_pressure": 2, "peace_pressure": 4}
            metric_deltas["民心"] = metric_deltas.get("民心", 0) - 1
        else:
            outcome = "小败"
            summary = "金军夜攻宣化门，夜值一度散乱，虽未破城，却烧毁城楼器械，主和派借势鼓噪。"
            changes = {"city_defense": -12, "defender_will": -7, "gate_risk": 10, "jin_pressure": 8, "peace_pressure": 12}
            metric_deltas["民心"] = metric_deltas.get("民心", 0) - 5
            self.db.change_issue("defend_bianjing", -10)
        for key, delta in changes.items():
            siege_deltas[key] = siege_deltas.get(key, 0) + delta
        self.db.conn.execute(
            "UPDATE city_gates SET condition = ?, risk = ?, status = ? WHERE id = 'xuanhua_gate'",
            (
                clamp(gate_condition + changes.get("city_defense", -4), 0, 100),
                clamp(int(gate.get("risk", 0)) + changes.get("gate_risk", -2), 0, 100),
                "稍安" if outcome == "小胜" else "危",
            ),
        )
        self.db.conn.execute(
            """INSERT INTO battle_reports
               (turn, title, summary, outcome, reasons_json, losses_json, changes_json)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                turn,
                "宣化门夜攻",
                summary,
                outcome,
                json.dumps(reasons, ensure_ascii=False),
                json.dumps({"守军": "伤亡数百", "城防": "城楼与器械受损"}, ensure_ascii=False),
                json.dumps(changes, ensure_ascii=False),
            ),
        )
        timeline.append(summary)

    def _check_ending(self, next_turn: int) -> str:
        game = self.db.row("SELECT ended, ending FROM game_state WHERE id = 1") or {}
        if game.get("ended"):
            return str(game.get("ending") or "")
        siege = self.db.row("SELECT * FROM siege_state WHERE id = 1") or {}
        metrics = {item["key"]: item["value"] for item in self.db.rows("SELECT key, value FROM metrics")}
        ending = ""
        if int(siege.get("city_defense", 0)) <= 18 and int(siege.get("defender_will", 0)) <= 28 and int(siege.get("gate_risk", 0)) >= 70:
            ending = "汴京城破：城防、战意与城门风险同时崩坏。"
        elif int(siege.get("peace_pressure", 0)) >= 86 and int(metrics.get("君威", 50)) <= 36:
            ending = "降议得逞：主和压力压过君威，朝堂绕过圣断接受苛约。"
        elif next_turn >= 6 and int(siege.get("city_defense", 0)) >= 58 and int(siege.get("defender_will", 0)) >= 52 and int(siege.get("jin_pressure", 0)) <= 72:
            ending = "五回合试玩终章：汴京保卫初成，金军暂缓强攻。"
        elif next_turn >= 6:
            ending = "五回合试玩终章：汴京仍危，金军、粮价与主和压力尚未解除。"
        if ending:
            self.db.conn.execute("UPDATE game_state SET ended = 1, ending = ?, phase = '结局' WHERE id = 1", (ending,))
        return ending

    def _record_ledger(
        self,
        turn: int,
        account: str,
        delta: int,
        category: str,
        reason: str,
        source: str,
        visibility: str = "公开",
    ) -> int:
        current = self.db.value(account)
        balance = self.db.change_metric(account, delta, high=999)
        self.db.conn.execute(
            """INSERT INTO economy_ledger
               (turn, account, delta, balance_after, category, reason, source, visibility)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (turn, account, balance - current, balance, category, reason, source, visibility),
        )
        return balance

    def _apply_faction_clocks(
        self,
        metric_deltas: dict[str, int],
        siege_deltas: dict[str, int],
        timeline: list[str],
    ) -> list[str]:
        warnings: list[str] = []
        clocks = self.db.rows("SELECT * FROM faction_clocks WHERE status = 'active' ORDER BY value DESC")
        for clock in clocks:
            stage = int(clock.get("stage", 0))
            if stage <= 0:
                continue
            clock_id = clock["id"]
            if clock_id == "transport_slowdown":
                self.db.change_route(
                    "jianghuai_grain_to_bianjing",
                    {"risk": stage + 1, "corruption": stage, "eta": 1 if stage >= 3 else 0},
                )
                self.db.change_route_node("bian_river_convoy", {"risk": stage + 2, "progress": -stage, "status": "转运迟滞"})
                if stage >= 2:
                    metric_deltas["京城粮"] = metric_deltas.get("京城粮", 0) - 1
                    timeline.append("转运财税网络开始怠工，江淮粮船报称水程、账册皆有阻滞。")
                if stage >= 3:
                    warnings.append("转运怠工已拖慢粮道，下月宜护粮、查账或保价催运。")
                    self.db.upsert_event(
                        {
                            "id": "clock_transport_slowdown",
                            "title": "转运怠工成势",
                            "kind": "暗潮",
                            "summary": "转运节点互相推诿，粮船脚价、账册和护送都成了拖延借口。",
                            "urgency": 78,
                            "severity": 72,
                            "credibility": 70,
                            "interests": ["转运财税网络", "粮道", "户部"],
                            "audiences": ["户部尚书", "转运判官"],
                            "actions": ["查账问责", "派兵护粮", "保价催运"],
                            "status": "active",
                            "read": 0,
                            "focus": 1,
                        }
                    )
            elif clock_id == "western_army_grievance":
                self.db.change_route("shaanxi_relief_army", {"risk": stage + 2, "eta": 1 if stage >= 3 else 0, "current_load": -1})
                self.db.change_route_node("hezhong_crossing", {"risk": stage + 3, "progress": -stage, "status": "西军观望"})
                if stage >= 2:
                    siege_deltas["qinwang_response"] = siege_deltas.get("qinwang_response", 0) - 3
                    timeline.append("陕西西军因赏格未实而观望，勤王路线又迟一线。")
                if stage >= 3:
                    warnings.append("西军怨望升高，勤王响应会继续被拖慢。")
            elif clock_id == "southern_flight_talk":
                if stage >= 2:
                    siege_deltas["peace_pressure"] = siege_deltas.get("peace_pressure", 0) + 3
                    metric_deltas["君威"] = metric_deltas.get("君威", 0) - 1
                    timeline.append("内廷南迁暗议外泄，主和压力随之上升。")
                if stage >= 3:
                    warnings.append("南迁暗议逼近失控，需用城防胜算和内廷安抚压住。")
            elif clock_id == "li_gang_removal":
                if stage >= 2:
                    siege_deltas["peace_pressure"] = siege_deltas.get("peace_pressure", 0) + 2
                    timeline.append("主和派借李纲专权之名弹劾，守城指挥承压。")
                if stage >= 3:
                    warnings.append("罢李纲风波已成案，守城体系可能被朝争摇动。")
            elif clock_id == "grain_market_strike":
                if stage >= 2:
                    self.db.change_route_node("capital_grain_market", {"risk": stage + 4, "progress": -stage, "status": "粮行观望"})
                    siege_deltas["grain_price"] = siege_deltas.get("grain_price", 0) + 7
                    metric_deltas["民心"] = metric_deltas.get("民心", 0) - 1
                    timeline.append("粮行观望闭市，坊市米价再起波澜。")
                if stage >= 3:
                    warnings.append("粮行罢市会推高粮价，需保价、护商并限价平粜。")
        return warnings

    def route_action(self, route_id: str, action: str = "escort", node_id: str | None = None) -> dict[str, Any]:
        route = self.db.row("SELECT * FROM logistics_routes WHERE id = ?", (route_id,))
        if not route:
            raise KeyError("未找到此路线。")
        selected_node = None
        if node_id:
            selected_node = self.db.row("SELECT * FROM route_nodes WHERE id = ? AND route_id = ?", (node_id, route_id))
            if not selected_node:
                raise KeyError("未找到此路线节点。")
        game = self.db.row("SELECT * FROM game_state WHERE id = 1") or {"turn": 1}
        turn = int(game.get("turn", 1))
        action = action or "escort"
        with self.db.conn:
            route_nodes = self.db.rows("SELECT * FROM route_nodes WHERE route_id = ? ORDER BY risk DESC, rowid", (route_id,))
            updated_node: dict[str, Any] | None = None

            def pick_node(kinds: set[str] | None = None) -> dict[str, Any] | None:
                if selected_node:
                    return selected_node
                if kinds:
                    return next((node for node in route_nodes if node["kind"] in kinds), None)
                return route_nodes[0] if route_nodes else None

            def change_node(changes: dict[str, int | str], kinds: set[str] | None = None) -> dict[str, Any] | None:
                nonlocal updated_node
                node = pick_node(kinds)
                if not node:
                    return None
                updated_node = self.db.change_route_node(node["id"], changes)
                return updated_node

            if action == "escort":
                self._record_ledger(turn, "国库", -2, "路线行动", f"派兵护送{route['name']}", "战区路线")
                updated = self.db.change_route(route_id, {"risk": -8, "escort": 14, "status": "护送"})
                change_node({"risk": -8, "progress": 8, "status": "护送中"})
                if route_id == "jianghuai_grain_to_bianjing":
                    self.db.change_siege("grain_price", -4, high=300)
                    self.db.change_faction_clock("grain_market_strike", -4)
                result = "已派兵护送，路线风险下降，但国库添了一笔护送开销。"
            elif action == "audit":
                updated = self.db.change_route(route_id, {"risk": 2, "corruption": -10, "status": "查账"})
                change_node({"risk": 3, "progress": 7, "status": "清查账册"}, {"warehouse", "collection", "river"})
                self.db.change_faction_clock("transport_slowdown", 8)
                result = "已点名查账，截留会收敛，转运网络也会记下这笔账。"
            elif action == "subsidy":
                self._record_ledger(turn, "国库", -4, "路线行动", f"给付{route['name']}脚价与保价", "战区路线")
                updated = self.db.change_route(route_id, {"risk": -5, "corruption": -4, "current_load": 6, "status": "保价催运"})
                change_node({"risk": -7, "progress": 14, "status": "保价开动"}, {"market", "warehouse", "collection"})
                self.db.change_faction_clock("grain_market_strike", -8)
                self.db.change_faction_clock("transport_slowdown", -4)
                self.db.change_siege("grain_price", -6, high=300)
                result = "脚价和保价落定，粮商愿意出船，粮价压力小退。"
            elif action == "reroute":
                self._record_ledger(turn, "国库", -1, "路线行动", f"{route['name']}临时改道", "战区路线")
                updated = self.db.change_route(route_id, {"risk": -10, "eta": 1, "current_load": -1, "status": "改道"})
                change_node({"risk": -10, "progress": -3, "status": "绕行避险"})
                result = "路线改道避开最险节点，但到达时间会被拉长。"
            elif action == "reward":
                if route_id != "shaanxi_relief_army":
                    raise ValueError("加赏催援只适用于勤王路线。")
                self._record_ledger(turn, "国库", -5, "勤王赏格", "兑现西军入援赏格", "战区路线")
                updated = self.db.change_route(route_id, {"risk": -6, "eta": -1, "current_load": 10, "escort": 6, "status": "加赏集结"})
                change_node({"risk": -6, "progress": 12, "status": "赏格已明"}, {"intercept", "relay"})
                self.db.change_siege("qinwang_response", 8)
                self.db.change_issue("qinwang_call", 8)
                self.db.change_faction_clock("western_army_grievance", -12)
                result = "赏格写清且先拨一批，西军集结更实，勤王响应上升。"
            elif action == "envoy":
                if route_id != "shaanxi_relief_army":
                    raise ValueError("遣使催促只适用于勤王路线。")
                self._record_ledger(turn, "国库", -1, "勤王使费", "遣中使催促西军行营", "战区路线")
                updated = self.db.change_route(route_id, {"risk": -3, "eta": -1, "status": "中使催促"})
                change_node({"risk": -4, "progress": 8, "status": "中使抵达"}, {"intercept", "relay"})
                self.db.change_siege("qinwang_response", 4)
                self.db.change_issue("qinwang_call", 4)
                self.db.change_faction_clock("western_army_grievance", -5)
                result = "中使持诏催促，勤王路线略有提速。"
            elif action == "secure_node":
                self._record_ledger(turn, "国库", -2, "节点固护", f"固护{route['name']}关键节点", "战区路线")
                updated = self.db.change_route(route_id, {"risk": -6, "escort": 8, "status": "节点固护"})
                node = change_node({"risk": -12, "progress": 10, "status": "已固护"})
                if route_id == "shaanxi_relief_army":
                    self.db.change_siege("qinwang_response", 2)
                result = f"已固护{node['name'] if node else route['name']}，局部风险下降，路线更可追溯。"
            elif action == "clear_intercept":
                if route_id != "shaanxi_relief_army":
                    raise ValueError("清截击只适用于勤王路线。")
                self._record_ledger(turn, "国库", -3, "勤王接应", "派兵清理勤王路截击点", "战区路线")
                updated = self.db.change_route(route_id, {"risk": -10, "eta": -1, "current_load": 6, "status": "清截击"})
                node = change_node({"risk": -16, "progress": 16, "status": "截击已清"}, {"intercept", "relay"})
                self.db.change_siege("qinwang_response", 6)
                self.db.change_issue("qinwang_call", 5)
                self.db.change_faction_clock("western_army_grievance", -10)
                result = f"{node['name'] if node else '勤王路'}截击稍解，西军入援更可信。"
            elif action == "receive":
                self._record_ledger(turn, "国库", -2, "路线接应", f"为{route['name']}安排接应", "战区路线")
                if route_id == "shaanxi_relief_army":
                    updated = self.db.change_route(route_id, {"risk": -7, "eta": -1, "current_load": 8, "status": "接应入援"})
                    node = change_node({"risk": -8, "progress": 18, "status": "接应已定"}, {"arrival", "relay"})
                    self.db.change_siege("qinwang_response", 5)
                    self.db.change_siege("defender_will", 2)
                    result = f"{node['name'] if node else '勤王接应'}已有章程，守军听闻援兵将近。"
                else:
                    updated = self.db.change_route(route_id, {"risk": -5, "eta": -1, "current_load": 8, "status": "接粮入仓"})
                    node = change_node({"risk": -7, "progress": 18, "status": "接粮入仓"}, {"market", "collection", "warehouse"})
                    self.db.change_metric("京城粮", 6)
                    self.db.change_metric("民心", 1)
                    self.db.change_siege("grain_price", -5, high=300)
                    result = f"{node['name'] if node else '粮道'}已有接收仓口，京城粮储回升。"
            elif action == "restore_credit":
                if route_id == "shaanxi_relief_army":
                    raise ValueError("恢复商户信用只适用于粮运路线。")
                self._record_ledger(turn, "国库", -3, "商户信用", "给付脚价并保护正常粮商", "战区路线")
                updated = self.db.change_route(route_id, {"risk": -4, "corruption": -6, "status": "恢复信用"})
                node = change_node({"risk": -8, "progress": 18, "status": "信用回升"}, {"market", "collection", "warehouse"})
                self.db.change_metric("民心", 2)
                self.db.change_siege("grain_price", -8, high=300)
                self.db.change_faction_clock("grain_market_strike", -10)
                self.db.change_faction_clock("transport_slowdown", -4)
                result = f"{node['name'] if node else '粮运节点'}信用稍复，粮商愿意明面交易。"
            else:
                raise ValueError("未知路线行动。")
            self.db.conn.execute(
                """INSERT INTO memories
                   (subject_type, subject_id, turn, title, cause, process, outcome, sentiment, importance, tags)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    "route",
                    route_id,
                    turn,
                    f"{route['name']}路线处置",
                    "围城压力使粮道与勤王路线成为要害。",
                    f"皇帝选择路线行动：{action}。",
                    result,
                    "positive",
                    3,
                    json.dumps(["路线行动", route["name"]], ensure_ascii=False),
                ),
            )
        return {"route": updated, "node": updated_node, "result": result, "state": self.state()}

    def mitigate_faction_clock(self, clock_id: str, action: str = "appease") -> dict[str, Any]:
        clock = self.db.row("SELECT * FROM faction_clocks WHERE id = ?", (clock_id,))
        if not clock:
            raise KeyError("未找到此反扑时钟。")
        game = self.db.row("SELECT * FROM game_state WHERE id = 1") or {"turn": 1}
        turn = int(game.get("turn", 1))
        with self.db.conn:
            if clock_id == "transport_slowdown":
                self._record_ledger(turn, "国库", -3, "派系缓和", "给付转运脚价并核关键节点", "人物谱")
                self.db.change_route("jianghuai_grain_to_bianjing", {"risk": -4, "corruption": -2, "status": "缓和转运"})
                self.db.change_route_node("bian_river_convoy", {"risk": -7, "progress": 8, "status": "缓和转运"})
                next_clock = self.db.change_faction_clock(clock_id, -12)
                result = "脚价与问责并行，转运怠工暂被压住。"
            elif clock_id == "western_army_grievance":
                self._record_ledger(turn, "国库", -4, "派系缓和", "预支西军赏格与军粮承诺", "人物谱")
                self.db.change_route("shaanxi_relief_army", {"eta": -1, "current_load": 4, "status": "安抚西军"})
                self.db.change_route_node("hezhong_crossing", {"risk": -8, "progress": 10, "status": "西军愿动"})
                self.db.change_route_node("hedong_relay", {"risk": -5, "progress": 8, "status": "接应有诺"})
                self.db.change_siege("qinwang_response", 5)
                next_clock = self.db.change_faction_clock(clock_id, -12)
                result = "赏格先落一半，西军怨望回落。"
            elif clock_id == "grain_market_strike":
                self._record_ledger(turn, "国库", -2, "派系缓和", "保价收粮并护正常商户", "人物谱")
                self.db.change_route_node("capital_grain_market", {"risk": -9, "progress": 12, "status": "开市有信"})
                self.db.change_siege("grain_price", -8, high=300)
                next_clock = self.db.change_faction_clock(clock_id, -10)
                result = "保价和护商令粮行愿意开市，粮价压力下降。"
            elif clock_id == "southern_flight_talk":
                self.db.change_metric("君威", 1)
                self.db.change_siege("peace_pressure", -5)
                next_clock = self.db.change_faction_clock(clock_id, -9)
                result = "召宗室入宫明示守城章程，南迁暗议暂退。"
            elif clock_id == "li_gang_removal":
                self.db.change_metric("君威", 1)
                self.db.change_siege("peace_pressure", -4)
                next_clock = self.db.change_faction_clock(clock_id, -9)
                result = "以战报和期限约束李纲权责，弹劾声势暂缓。"
            else:
                next_clock = self.db.change_faction_clock(clock_id, -8)
                result = "已安抚关键人等，反扑声量下降。"
            if action == "pressure":
                self.db.conn.execute("UPDATE factions SET fear = fear + 3, backlash = backlash + 2 WHERE id = ?", (clock["faction_id"],))
            elif action == "expose":
                self.db.conn.execute("UPDATE factions SET fear = fear + 2, affinity = affinity - 1 WHERE id = ?", (clock["faction_id"],))
            else:
                self.db.conn.execute("UPDATE factions SET affinity = affinity + 2, fear = CASE WHEN fear >= 1 THEN fear - 1 ELSE fear END WHERE id = ?", (clock["faction_id"],))
            self.db.conn.execute(
                """INSERT INTO memories
                   (subject_type, subject_id, turn, title, cause, process, outcome, sentiment, importance, tags)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    "faction_clock",
                    clock_id,
                    turn,
                    f"{clock['title']}缓和",
                    clock["trigger"],
                    f"皇帝采取{action}处置。",
                    result,
                    "mixed",
                    3,
                    json.dumps(["反扑时钟", clock["title"]], ensure_ascii=False),
                ),
            )
        return {"clock": next_clock, "result": result, "state": self.state()}

    def _create_diplomacy_term(
        self,
        *,
        title: str,
        kind: str,
        turn: int,
        due_in: int,
        compliance: int,
        breach_risk: int,
        summary: str,
        demand: str,
    ) -> dict[str, Any]:
        return self.db.create_diplomacy_term(
            {
                "title": title,
                "kind": kind,
                "due_turn": turn + due_in,
                "compliance": compliance,
                "breach_risk": breach_risk,
                "summary": summary,
                "demand": demand,
                "created_turn": turn,
            }
        )

    def _draft_treaty_text(self, term: dict[str, Any]) -> str:
        return (
            f"草约：一，宋廷仍以“{term['title']}”为前议，限第 {int(term['due_turn']) + 1} 回合前补足回书、使费与犒军凭据；"
            "二，金营暂缓强攻，但保留复索犒军、质子与罢免主战臣之议；"
            "三，若再以空文迁延，往返使节由金营留验，攻守后果各自承担。"
        )

    def _create_diplomacy_incident_from_breach(self, term: dict[str, Any], turn: int) -> dict[str, Any]:
        existing = self.db.row(
            "SELECT * FROM diplomacy_incidents WHERE kind = 'detained_envoy' AND status = 'active' ORDER BY id DESC LIMIT 1"
        )
        if existing:
            return existing
        return self.db.create_diplomacy_incident(
            {
                "title": "金营扣留宋使",
                "kind": "detained_envoy",
                "status": "active",
                "envoy_name": "往返国书使",
                "jin_actor": "东路军都监",
                "deadline_turn": turn + 2,
                "severity": 58 + min(22, int(term["breach_risk"]) // 4),
                "leverage": max(18, 48 - int(term["compliance"]) // 2),
                "summary": f"因“{term['title']}”失信，金营扣留往返国书使，要求宋廷补足犒军与正式回书。",
                "demand": term["demand"],
                "treaty_text": self._draft_treaty_text(term),
                "created_turn": turn,
            }
        )

    def _resolve_diplomacy_terms(
        self,
        turn: int,
        metric_deltas: dict[str, int],
        siege_deltas: dict[str, int],
        diplomacy_deltas: dict[str, int],
        timeline: list[str],
        warnings: list[str],
    ) -> None:
        terms = self.db.rows("SELECT * FROM diplomacy_terms WHERE status = 'active' ORDER BY due_turn, id")
        for term in terms:
            due_turn = int(term["due_turn"])
            compliance = int(term["compliance"])
            breach_risk = int(term["breach_risk"])
            kind = term["kind"]
            if due_turn > turn + 1:
                if kind in {"stall", "tribute"}:
                    diplomacy_deltas["impatience"] = diplomacy_deltas.get("impatience", 0) - 2
                continue

            if compliance >= 65 or breach_risk <= 25:
                result = f"{term['title']}勉强履行，金营暂缓攻势，宋方又争得一段修城、催粮和勤王时间。"
                self.db.change_diplomacy_term(int(term["id"]), {"status": "fulfilled", "result": result})
                diplomacy_deltas["trust"] = diplomacy_deltas.get("trust", 0) + 5
                diplomacy_deltas["impatience"] = diplomacy_deltas.get("impatience", 0) - 7
                diplomacy_deltas["demand_severity"] = diplomacy_deltas.get("demand_severity", 0) - 4
                siege_deltas["jin_pressure"] = siege_deltas.get("jin_pressure", 0) - 4
                if kind == "divide":
                    diplomacy_deltas["internal_tension"] = diplomacy_deltas.get("internal_tension", 0) + 8
                    diplomacy_deltas["leverage"] = diplomacy_deltas.get("leverage", 0) + 4
                    siege_deltas["jin_pressure"] = siege_deltas.get("jin_pressure", 0) - 3
                timeline.append(result)
                sentiment = "positive"
            else:
                result = f"{term['title']}失信，金营斥宋廷反复，使节被留难，攻城与索约口气一并转硬。"
                self.db.change_diplomacy_term(int(term["id"]), {"status": "breached", "result": result})
                diplomacy_deltas["trust"] = diplomacy_deltas.get("trust", 0) - 9
                diplomacy_deltas["impatience"] = diplomacy_deltas.get("impatience", 0) + 11
                diplomacy_deltas["demand_severity"] = diplomacy_deltas.get("demand_severity", 0) + 8
                siege_deltas["jin_pressure"] = siege_deltas.get("jin_pressure", 0) + 8
                siege_deltas["peace_pressure"] = siege_deltas.get("peace_pressure", 0) + 4
                metric_deltas["君威"] = metric_deltas.get("君威", 0) - 2
                warnings.insert(0, "外交条款失信，金营可能扣使、加索金银或转入再攻。")
                timeline.append(result)
                incident = self._create_diplomacy_incident_from_breach(term, turn)
                self.db.upsert_event(
                    {
                        "id": f"diplomacy_breach_{term['id']}",
                        "title": "金营斥宋失信",
                        "kind": "外交",
                        "summary": f"金使称宋廷只以空文拖延，{incident['jin_actor']}留难{incident['envoy_name']}，并把犒军、质子和罢免主战臣一并加码。",
                        "urgency": 82,
                        "severity": 74,
                        "credibility": 72,
                        "interests": ["金营", "主和派", "皇城司"],
                        "audiences": ["主和宰执", "皇城司使", "李纲"],
                        "actions": ["赎回使节", "密取使节", "拒割地质子"],
                        "status": "active",
                        "read": 0,
                        "focus": 1,
                    }
                )
                sentiment = "negative"

            self.db.conn.execute(
                """INSERT INTO memories
                   (subject_type, subject_id, turn, title, cause, process, outcome, sentiment, importance, tags)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    "diplomacy_term",
                    str(term["id"]),
                    turn,
                    f"外交条款：{term['title']}",
                    term["demand"],
                    term["summary"],
                    result,
                    sentiment,
                    4,
                    json.dumps(["金宋谈判", "外交条款", term["title"]], ensure_ascii=False),
                ),
            )

    def _resolve_diplomacy_incidents(
        self,
        turn: int,
        metric_deltas: dict[str, int],
        siege_deltas: dict[str, int],
        diplomacy_deltas: dict[str, int],
        timeline: list[str],
        warnings: list[str],
    ) -> None:
        incidents = self.db.rows("SELECT * FROM diplomacy_incidents WHERE status = 'active' ORDER BY deadline_turn, id")
        for incident in incidents:
            severity = int(incident["severity"])
            deadline_turn = int(incident["deadline_turn"])
            if deadline_turn > turn + 1:
                if severity >= 70:
                    diplomacy_deltas["impatience"] = diplomacy_deltas.get("impatience", 0) + 2
                    warnings.insert(0, f"{incident['title']}仍未处置，{incident['jin_actor']}催索草约回书。")
                continue

            result = f"{incident['title']}拖过限期，{incident['jin_actor']}公开辱使并加索犒军，主和派借此逼请真和。"
            self.db.change_diplomacy_incident(
                int(incident["id"]),
                {"status": "escalated", "severity": 18, "resolution": result},
            )
            diplomacy_deltas["trust"] = diplomacy_deltas.get("trust", 0) - 8
            diplomacy_deltas["impatience"] = diplomacy_deltas.get("impatience", 0) + 12
            diplomacy_deltas["demand_severity"] = diplomacy_deltas.get("demand_severity", 0) + 7
            siege_deltas["jin_pressure"] = siege_deltas.get("jin_pressure", 0) + 7
            siege_deltas["peace_pressure"] = siege_deltas.get("peace_pressure", 0) + 6
            metric_deltas["君威"] = metric_deltas.get("君威", 0) - 3
            warnings.insert(0, "扣使风波升级，若不立刻守住割地质子底线，朝堂会被真和议牵走。")
            timeline.append(result)
            self.db.upsert_event(
                {
                    "id": f"diplomacy_envoy_escalation_{incident['id']}",
                    "title": "扣使风波升级",
                    "kind": "外交",
                    "summary": "金营公开辱使并递出更硬草约，主和派称唯有真和才能保城。",
                    "urgency": 86,
                    "severity": 78,
                    "credibility": 76,
                    "interests": ["金营", "主和派", "台谏清议"],
                    "audiences": ["主和宰执", "李纲", "皇城司使"],
                    "actions": ["拒割地质子", "强硬拒使", "分化金营"],
                    "status": "active",
                    "read": 0,
                    "focus": 1,
                }
            )
            self.db.conn.execute(
                """INSERT INTO memories
                   (subject_type, subject_id, turn, title, cause, process, outcome, sentiment, importance, tags)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    "diplomacy_incident",
                    str(incident["id"]),
                    turn,
                    incident["title"],
                    incident["summary"],
                    "宋廷未能在限期前处置扣使。",
                    result,
                    "negative",
                    4,
                    json.dumps(["金宋谈判", "扣使", incident["title"]], ensure_ascii=False),
                ),
            )

    def diplomacy_action(self, action: str = "stall") -> dict[str, Any]:
        diplomacy = self.db.row("SELECT * FROM diplomacy_state WHERE id = 1")
        if not diplomacy:
            raise KeyError("未找到外交状态。")
        game = self.db.row("SELECT * FROM game_state WHERE id = 1") or {"turn": 1}
        turn = int(game.get("turn", 1))
        action = action or "stall"
        with self.db.conn:
            if action == "stall":
                self._record_ledger(turn, "国库", -3, "外交礼物", "假议和往返犒军与使费", "金宋谈判")
                self.db.change_diplomacy("trust", 3)
                self.db.change_diplomacy("impatience", -13)
                self.db.change_diplomacy("leverage", 3)
                self.db.change_diplomacy("demand_severity", 2)
                self.db.change_siege("jin_pressure", -5)
                self.db.change_siege("peace_pressure", 6)
                self.db.change_metric("君威", -2)
                self.db.change_faction_clock("southern_flight_talk", 4)
                self.db.change_faction_clock("li_gang_removal", 3)
                self._create_diplomacy_term(
                    title="三日复命缓攻",
                    kind="stall",
                    turn=turn,
                    due_in=2,
                    compliance=42,
                    breach_risk=48,
                    summary="使者承诺三日一复命，以含混国书争取修城与勤王时间。",
                    demand=str(diplomacy.get("current_demand", "")),
                )
                status = "拖延谈判"
                result = "使者以复命、犒军和含混文字争得缓冲，金军攻势稍缓，主和派却更敢言和。"
            elif action == "tribute":
                if self.db.value("国库") <= 0:
                    raise ValueError("国库已空，无法犒军。")
                self._record_ledger(turn, "国库", -8, "外交礼物", "犒军金银换取暂缓攻城", "金宋谈判")
                self.db.change_diplomacy("demand_severity", -8)
                self.db.change_diplomacy("trust", 6)
                self.db.change_diplomacy("impatience", -12)
                self.db.change_siege("jin_pressure", -8)
                self.db.change_siege("peace_pressure", 5)
                self.db.change_metric("君威", -4)
                self.db.change_faction_clock("southern_flight_talk", 6)
                self.db.change_faction_clock("li_gang_removal", 4)
                self._create_diplomacy_term(
                    title="犒军暂缓约",
                    kind="tribute",
                    turn=turn,
                    due_in=2,
                    compliance=58,
                    breach_risk=34,
                    summary="宋廷先送一笔犒军银，承诺下月补足使费与回书，以换取金营暂缓攻城。",
                    demand=str(diplomacy.get("current_demand", "")),
                )
                status = "犒军暂缓"
                result = "犒军银送入金营，攻城节奏暂缓；朝中亦有人以此为真和议张本。"
            elif action == "honor_terms":
                active_term = self.db.row(
                    "SELECT * FROM diplomacy_terms WHERE status = 'active' ORDER BY due_turn, id LIMIT 1"
                )
                if not active_term:
                    raise ValueError("当前没有待履约外交条款。")
                if active_term["kind"] == "divide":
                    if self.db.value("内帑") < 2:
                        raise ValueError("内帑不足，无法续接金营暗线。")
                    self._record_ledger(turn, "内帑", -2, "外交履约", f"续接{active_term['title']}暗线", "金宋谈判", "秘密")
                    result = "皇城司续给暗线银，金营争功之隙仍可利用。"
                else:
                    if self.db.value("国库") < 4:
                        raise ValueError("国库不足，无法补足外交使费。")
                    self._record_ledger(turn, "国库", -4, "外交履约", f"补足{active_term['title']}使费", "金宋谈判")
                    result = "使费、回书与犒军尾款补上，金营暂少了一个翻脸借口。"
                self.db.change_diplomacy_term(int(active_term["id"]), {"compliance": 25, "breach_risk": -20})
                self.db.change_diplomacy("trust", 4)
                self.db.change_diplomacy("impatience", -5)
                self.db.change_diplomacy("leverage", 2)
                self.db.change_siege("peace_pressure", 2)
                status = "补足条款"
            elif action == "redeem_envoy":
                incident = self.db.row(
                    "SELECT * FROM diplomacy_incidents WHERE status = 'active' ORDER BY deadline_turn, id LIMIT 1"
                )
                if not incident:
                    raise ValueError("当前没有待处置扣使事件。")
                if self.db.value("国库") < 5:
                    raise ValueError("国库不足，无法赎回使节。")
                self._record_ledger(turn, "国库", -5, "扣使赎回", f"赎回{incident['envoy_name']}并补草约使费", "金宋谈判")
                result = f"宋廷补给犒军尾款与正式回书，{incident['envoy_name']}得返，金营少了继续辱使的借口。"
                self.db.change_diplomacy_incident(
                    int(incident["id"]),
                    {"status": "resolved", "severity": -35, "leverage": 6, "resolution": result},
                )
                self.db.change_diplomacy("trust", 6)
                self.db.change_diplomacy("impatience", -8)
                self.db.change_diplomacy("demand_severity", -3)
                self.db.change_siege("jin_pressure", -2)
                self.db.change_siege("peace_pressure", 3)
                self.db.change_metric("君威", -2)
                self.db.change_faction_clock("southern_flight_talk", 4)
                status = "赎回使节"
            elif action == "extract_envoy":
                incident = self.db.row(
                    "SELECT * FROM diplomacy_incidents WHERE status = 'active' ORDER BY deadline_turn, id LIMIT 1"
                )
                if not incident:
                    raise ValueError("当前没有待处置扣使事件。")
                if self.db.value("内帑") < 3:
                    raise ValueError("内帑不足，无法密取使节。")
                self._record_ledger(turn, "内帑", -3, "扣使密取", f"打通金营暗线接出{incident['envoy_name']}", "金宋谈判", "秘密")
                result = f"皇城司借金营争功缝隙接出{incident['envoy_name']}，草约副本亦被带回御前。"
                self.db.change_diplomacy_incident(
                    int(incident["id"]),
                    {"status": "resolved", "severity": -25, "leverage": 12, "resolution": result},
                )
                self.db.change_diplomacy("trust", -4)
                self.db.change_diplomacy("impatience", -4)
                self.db.change_diplomacy("internal_tension", 8)
                self.db.change_diplomacy("leverage", 5)
                self.db.change_siege("jin_pressure", -3)
                self.db.change_siege("peace_pressure", -1)
                status = "密取使节"
            elif action == "abandon_envoy":
                incident = self.db.row(
                    "SELECT * FROM diplomacy_incidents WHERE status = 'active' ORDER BY deadline_turn, id LIMIT 1"
                )
                if not incident:
                    raise ValueError("当前没有待处置扣使事件。")
                result = f"御前明示不以使节受辱换割地质子，{incident['envoy_name']}仍陷金营，朝中战和分野更明。"
                self.db.change_diplomacy_incident(
                    int(incident["id"]),
                    {"status": "abandoned", "severity": 10, "leverage": 4, "resolution": result},
                )
                self.db.change_diplomacy("trust", -12)
                self.db.change_diplomacy("impatience", 8)
                self.db.change_diplomacy("demand_severity", 6)
                self.db.change_diplomacy("leverage", 4)
                self.db.change_siege("jin_pressure", 6)
                self.db.change_siege("peace_pressure", -6)
                self.db.change_siege("defender_will", 4)
                self.db.change_metric("君威", 5)
                self.db.change_faction_clock("southern_flight_talk", -4)
                self.db.change_faction_clock("li_gang_removal", -2)
                status = "弃使明底线"
            elif action == "hardline":
                siege = self.db.row("SELECT * FROM siege_state WHERE id = 1") or {}
                leverage = int(diplomacy.get("leverage", 0))
                defense_total = int(siege.get("city_defense", 0)) + int(siege.get("defender_will", 0)) + leverage
                jin_delta = 3 if defense_total >= 125 else 7
                self.db.change_diplomacy("trust", -8)
                self.db.change_diplomacy("impatience", 8)
                self.db.change_diplomacy("leverage", 7)
                self.db.change_diplomacy("demand_severity", 3)
                self.db.change_siege("jin_pressure", jin_delta)
                self.db.change_siege("peace_pressure", -5)
                self.db.change_siege("defender_will", 5)
                self.db.change_metric("君威", 4)
                self.db.change_faction_clock("southern_flight_talk", -3)
                self.db.change_faction_clock("li_gang_removal", -2)
                status = "强硬拒使"
                result = "御前明言不受胁迫，禁军与主战清议振奋；金使怒归，攻城急躁也随之上升。"
            elif action == "divide":
                if self.db.value("内帑") < 2:
                    raise ValueError("内帑不足，无法秘密收买金营。")
                self._record_ledger(turn, "内帑", -4, "外交密支", "收买金营使者与部族耳目", "金宋谈判", "秘密")
                self.db.change_diplomacy("internal_tension", 16)
                self.db.change_diplomacy("leverage", 8)
                self.db.change_diplomacy("impatience", -6)
                self.db.change_diplomacy("demand_severity", -4)
                self.db.change_diplomacy("trust", -3)
                self.db.change_siege("jin_pressure", -4)
                self.db.change_siege("peace_pressure", -2)
                self._create_diplomacy_term(
                    title="金营争功暗线",
                    kind="divide",
                    turn=turn,
                    due_in=2,
                    compliance=50,
                    breach_risk=28,
                    summary="皇城司承诺继续给付暗线银，挑动金营诸部争功互疑。",
                    demand="金营诸部争功，东路军对攻城时机已有分歧。",
                )
                status = "离间金营"
                result = "皇城司暗线入金营，诸部争功互疑，宋方谈判筹码增加。"
                if int(diplomacy.get("internal_tension", 0)) + 16 >= 42:
                    self.db.upsert_event(
                        {
                            "id": "jin_camp_rivalry",
                            "title": "金营争功",
                            "kind": "密报",
                            "summary": "皇城司探得金营诸部争功，东路军对攻城时机已有分歧。",
                            "urgency": 72,
                            "severity": 58,
                            "credibility": 66,
                            "interests": ["金军", "皇城司", "外交"],
                            "audiences": ["皇城司使", "主和宰执"],
                            "actions": ["继续离间", "趁机修城", "催勤王"],
                            "status": "active",
                            "read": 0,
                            "focus": 1,
                        }
                    )
            elif action == "refuse_terms":
                severity = int(diplomacy.get("demand_severity", 0))
                if severity < 55:
                    raise ValueError("金营尚未正式抛出割地质子底线。")
                leverage = int(diplomacy.get("leverage", 0))
                self.db.change_diplomacy("trust", -10)
                self.db.change_diplomacy("impatience", 6)
                self.db.change_diplomacy("demand_severity", 5)
                self.db.change_diplomacy("leverage", 5)
                self.db.change_metric("君威", 6)
                self.db.change_siege("peace_pressure", -7)
                self.db.change_siege("defender_will", 3)
                self.db.change_siege("jin_pressure", -2 if leverage >= 45 else 5)
                self.db.change_faction_clock("southern_flight_talk", -4)
                self.db.change_faction_clock("li_gang_removal", -3)
                status = "拒割地质子"
                result = "御笔划定底线：割地、质子皆不可许。朝野稍振，金营亦随即加重言辞。"
            else:
                raise ValueError("未知外交行动。")

            latest = self.db.row("SELECT * FROM diplomacy_state WHERE id = 1") or diplomacy
            self.db.set_diplomacy_text(
                current_demand=self._diplomacy_demand_text(int(latest.get("demand_severity", 0))),
                status=status,
            )
            self.db.conn.execute(
                """INSERT INTO memories
                   (subject_type, subject_id, turn, title, cause, process, outcome, sentiment, importance, tags)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    "diplomacy",
                    action,
                    turn,
                    f"金宋谈判：{status}",
                    str(diplomacy.get("current_demand", "")),
                    f"皇帝选择外交行动：{action}。",
                    result,
                    "mixed",
                    4,
                    json.dumps(["金宋谈判", status], ensure_ascii=False),
                ),
            )
        return {"result": result, "diplomacy": self.db.row("SELECT * FROM diplomacy_state WHERE id = 1"), "state": self.state()}

    def resolve_turn(self) -> dict[str, Any]:
        state = self.db.row("SELECT * FROM game_state WHERE id = 1") or {}
        turn = int(state.get("turn", 1))
        if int(state.get("ended", 0)):
            return {"report": self.db.rows("SELECT * FROM turn_reports ORDER BY id DESC LIMIT 1")[0], "state": self.state(), "timeline": [], "metric_deltas": {}, "directive_results": []}
        directives = self.db.rows("SELECT * FROM directives WHERE status IN ('draft', 'confirmed') ORDER BY id")
        metric_deltas: dict[str, int] = {"京城粮": -2}
        siege_deltas: dict[str, int] = {"jin_pressure": 8, "peace_pressure": 4, "grain_price": 13}
        diplomacy_deltas: dict[str, int] = {"impatience": 5}
        timeline: list[str] = ["金军前锋逼近黄河，河北溃报入京。"]
        directive_results: list[dict[str, str]] = []
        clock_warnings: list[str] = []
        with self.db.conn:
            for directive in directives:
                title = directive["title"]
                result = "旨意已下，中书门下照会相关官署。"
                if "李纲" in title or "守城" in title or "宣化门" in title:
                    siege_deltas["city_defense"] = siege_deltas.get("city_defense", 0) + 8
                    siege_deltas["defender_will"] = siege_deltas.get("defender_will", 0) + 6
                    metric_deltas["君威"] = metric_deltas.get("君威", 0) + 3
                    self.db.change_issue("defend_bianjing", 10)
                    self.db.change_faction_clock("li_gang_removal", 7)
                    self.db.conn.execute("UPDATE city_gates SET condition = condition + 10, commander = '李纲', equipment = equipment + 8, status = '稍安' WHERE id = 'xuanhua_gate'")
                    result = "李纲亲至宣化门，工部料物不足仍先修城楼，殿前司夜值稍肃。"
                    timeline.append("宣化门守备稍稳，李纲受主战清议拥戴。")
                if "修城" in title or "火油" in title or "器械" in title:
                    metric_deltas["国库"] = metric_deltas.get("国库", 0) - 5
                    siege_deltas["city_defense"] = siege_deltas.get("city_defense", 0) + 7
                    siege_deltas["fire_risk"] = siege_deltas.get("fire_risk", 0) + 3
                    self.db.conn.execute("UPDATE city_gates SET condition = condition + 6, equipment = equipment + 10 WHERE id = 'xuanhua_gate'")
                    result = "工部仓促拨料，宣化门炮石与火油略足；但火油入城也提高仓储火患。"
                if "急饷" in title or "补禁军" in title or "内帑" in title:
                    metric_deltas["国库"] = metric_deltas.get("国库", 0) - 8
                    metric_deltas["内帑"] = metric_deltas.get("内帑", 0) - 5
                    metric_deltas["民心"] = metric_deltas.get("民心", 0) + 2
                    siege_deltas["defender_will"] = siege_deltas.get("defender_will", 0) + 4
                    self.db.change_issue("discipline_guards", 8)
                    self.db.change_faction_clock("transport_slowdown", 4)
                    self.db.change_faction_clock("southern_flight_talk", 3)
                    result = "内帑如数拨出，户部先发一半，开封府核验营册时发现发放旧账不清。"
                    timeline.append("禁军鼓噪暂息，但军饷去向暴露疑点。")
                if "夜值" in title or "城门" in title or "排查" in title:
                    siege_deltas["gate_risk"] = siege_deltas.get("gate_risk", 0) - 8
                    siege_deltas["defender_will"] = siege_deltas.get("defender_will", 0) + 2
                    metric_deltas["民心"] = metric_deltas.get("民心", 0) - 1
                    self.db.change_issue("discipline_guards", 6)
                    result = "殿前司重排夜值，开封府巡检城门；军心稍肃，坊市嫌夜禁过严。"
                if "勤王" in title or "西军" in title or "种师道" in title:
                    metric_deltas["国库"] = metric_deltas.get("国库", 0) - 3
                    siege_deltas["qinwang_response"] = siege_deltas.get("qinwang_response", 0) + 16
                    siege_deltas["jin_pressure"] = siege_deltas.get("jin_pressure", 0) - 2
                    self.db.change_issue("qinwang_call", 18)
                    self.db.change_route("shaanxi_relief_army", {"status": "集结", "eta": -1, "escort": 8, "current_load": 12})
                    self.db.change_route_node("hezhong_crossing", {"risk": -8, "progress": 14, "status": "西军渡河"})
                    self.db.change_route_node("hedong_relay", {"risk": -5, "progress": 10, "status": "接应待粮"})
                    self.db.change_faction_clock("western_army_grievance", -9)
                    result = "手诏传至陕西，种师道部开始集结；但赏格和军粮仍须兑现，否则行军会迟。"
                    timeline.append("西军由观望转入集结，勤王响应上升。")
                if "粮" in title or "平粜" in title or "开仓" in title:
                    metric_deltas["京城粮"] = metric_deltas.get("京城粮", 0) - 4
                    metric_deltas["民心"] = metric_deltas.get("民心", 0) + 3
                    siege_deltas["grain_price"] = siege_deltas.get("grain_price", 0) - 22
                    siege_deltas["defender_will"] = siege_deltas.get("defender_will", 0) + 3
                    self.db.change_route("jianghuai_grain_to_bianjing", {"risk": -5, "current_load": 4, "status": "催运"})
                    self.db.change_route_node("capital_grain_market", {"risk": -9, "progress": 12, "status": "开市平粜"})
                    self.db.change_route_node("bian_river_convoy", {"risk": -4, "progress": 8, "status": "催船北上"})
                    self.db.change_faction_clock("grain_market_strike", 6)
                    self.db.change_faction_clock("transport_slowdown", 4)
                    result = "开封府开仓平粜，米价暂缓；江淮粮道被催，但转运网络索要护粮与脚价。"
                    timeline.append("京城粮价稍稳，坊市民心回升。")
                if "议和" in title or "国书" in title or "金营" in title:
                    siege_deltas["jin_pressure"] = siege_deltas.get("jin_pressure", 0) - 5
                    siege_deltas["peace_pressure"] = siege_deltas.get("peace_pressure", 0) + 8
                    metric_deltas["君威"] = metric_deltas.get("君威", 0) - 2
                    diplomacy_deltas["trust"] = diplomacy_deltas.get("trust", 0) + 4
                    diplomacy_deltas["leverage"] = diplomacy_deltas.get("leverage", 0) + 3
                    diplomacy_deltas["impatience"] = diplomacy_deltas.get("impatience", 0) - 7
                    self.db.set_diplomacy_text(status="拖延谈判")
                    self.db.change_faction_clock("southern_flight_talk", 5)
                    self.db.change_faction_clock("li_gang_removal", 3)
                    result = "国书送至金营，争得数日缓冲；主战清议疑其开割地之门。"
                self.db.conn.execute("UPDATE directives SET status = 'issued', result_summary = ? WHERE id = ?", (result, directive["id"]))
                directive_results.append({"title": title, "result": result})
            self._complete_secret_orders(turn, timeline)
            if not any("勤王" in item["title"] or "西军" in item["title"] for item in directives):
                self.db.change_route("shaanxi_relief_army", {"eta": 1, "risk": 4})
                self.db.change_route_node("hezhong_crossing", {"risk": 5, "progress": -4, "status": "无人接应"})
                self.db.change_issue("qinwang_call", -4)
                self.db.change_faction_clock("western_army_grievance", 5)
            if not any("粮" in item["title"] or "平粜" in item["title"] or "开仓" in item["title"] for item in directives):
                self.db.change_route("jianghuai_grain_to_bianjing", {"risk": 3, "corruption": 2, "eta": 1})
                self.db.change_route_node("capital_grain_market", {"risk": 5, "progress": -5, "status": "粮行闭市"})
                self.db.change_route_node("bian_river_convoy", {"risk": 3, "progress": -3, "status": "水程迟滞"})
                self.db.change_faction_clock("transport_slowdown", 3)
                self.db.change_faction_clock("grain_market_strike", 4)
            clock_warnings = self._apply_faction_clocks(metric_deltas, siege_deltas, timeline)
            self._resolve_diplomacy_terms(turn, metric_deltas, siege_deltas, diplomacy_deltas, timeline, clock_warnings)
            self._resolve_diplomacy_incidents(turn, metric_deltas, siege_deltas, diplomacy_deltas, timeline, clock_warnings)
            self._resolve_night_attack(turn, metric_deltas, siege_deltas, timeline)
            for key, delta in metric_deltas.items():
                if delta:
                    high = 999 if key in {"国库", "内帑", "京城粮"} else 100
                    balance = self.db.change_metric(key, delta, high=high)
                    if key in {"国库", "内帑", "京城粮"}:
                        self.db.conn.execute(
                            """INSERT INTO economy_ledger
                               (turn, account, delta, balance_after, category, reason, source, visibility)
                               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                            (turn, key, delta, balance, "月末结算", "诏令执行与京城消耗", "月末回奏", "公开"),
                        )
            for key, delta in siege_deltas.items():
                if delta:
                    high = 300 if key == "grain_price" else 100
                    self.db.change_siege(key, delta, high=high)
            for key, delta in diplomacy_deltas.items():
                if delta:
                    self.db.change_diplomacy(key, delta)
            next_turn = turn + 1
            month_label = MONTHS[(next_turn - 1) % len(MONTHS)]
            phase = "证据与对质" if self.db.row("SELECT * FROM court_cases WHERE status = 'ready'") else "朝报"
            self.db.conn.execute(
                "UPDATE game_state SET turn = ?, month_label = ?, phase = ? WHERE id = 1",
                (next_turn, month_label, phase),
            )
            self.db.conn.execute("UPDATE events SET status = 'archived' WHERE id IN ('jin_southbound', 'guards_pay_arrears', 'li_gang_requests_defense')")
            if self.db.row("SELECT * FROM evidence_items WHERE id = 'dongcang副册'"):
                self.db.upsert_event(
                    {
                        "id": "dongcang_ledger_found",
                        "title": "东仓副册入宫",
                        "kind": "密奏",
                        "summary": "皇城司密查得东仓副册，拨付与实发数不合，可据此开禁军欠饷对质。",
                        "urgency": 88,
                        "severity": 76,
                        "credibility": 82,
                        "interests": ["皇城司", "户部", "转运财税网络"],
                        "audiences": ["皇城司使", "户部尚书", "转运判官"],
                        "actions": ["开殿前对质", "继续深查", "私下胁迫"],
                        "status": "active",
                        "read": 0,
                        "focus": 1,
                    }
                )
            self._schedule_historical_anchors(next_turn)
            ending = self._check_ending(next_turn)
            report_title = f"靖康元年{month_label}回奏"
            summary = "京城稍稳，禁军鼓噪暂息；然金军仍逼黄河，战和、粮价与勤王都已压到御案前。"
            if ending:
                summary = ending
            warnings = [
                "金军威压继续上升，需决定守城、议和或催勤王的先后。",
                "东仓副册可支撑殿前对质，但会触动转运财税网络。",
                "粮价仍涨，若不开仓调粮，民心将受损。",
            ]
            warnings.extend(clock_warnings[:2])
            if self.db.row("SELECT * FROM battle_reports WHERE turn = ?", (turn,)):
                warnings.insert(0, "宣化门夜攻战报已入史册，下一步应补城防损耗。")
            if not ending:
                summary = self._polish_report_summary(summary, timeline, directive_results, warnings).text
            self.db.conn.execute(
                """INSERT INTO turn_reports
                   (turn, title, summary, narrative, metrics_delta_json, timeline_json, directives_json, warnings_json)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    turn,
                    report_title,
                    summary,
                    "\n".join(timeline),
                    json.dumps(metric_deltas, ensure_ascii=False),
                    json.dumps(timeline, ensure_ascii=False),
                    json.dumps(directive_results, ensure_ascii=False),
                    json.dumps(warnings, ensure_ascii=False),
                ),
            )
            self.db.conn.execute(
                """INSERT INTO memories
                   (subject_type, subject_id, turn, title, cause, process, outcome, sentiment, importance, tags)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    "court",
                    "song_court",
                    turn,
                    "靖康月度处置",
                    "金军南下、禁军欠饷、战和与粮价相逼",
                    "皇帝召见重臣，调度守城、钱粮、密查、勤王与议和。",
                    summary,
                    "mixed",
                    4,
                    json.dumps(["月末回奏", "禁军欠饷", "汴京守备"], ensure_ascii=False),
                ),
            )
        return {
            "report": self.db.rows("SELECT * FROM turn_reports ORDER BY id DESC LIMIT 1")[0],
            "state": self.state(),
            "timeline": timeline,
            "metric_deltas": metric_deltas,
            "directive_results": directive_results,
        }

    def resolve_stream(self) -> Iterator[dict[str, Any]]:
        yield {"type": "stage", "message": "中书门下誊录诏令"}
        yield {"type": "stage", "message": "户部、皇城司、开封府回奏"}
        result = self.resolve_turn()
        yield {"type": "narrative", "message": result["report"]["summary"]}
        yield {"type": "done", "payload": result}

    def judge_case(self, case_id: str, judgment: str) -> dict[str, Any]:
        case = self.db.row("SELECT * FROM court_cases WHERE id = ?", (case_id,))
        if not case:
            raise KeyError("未找到案件。")
        if case["status"] not in {"ready", "judged"}:
            raise ValueError("此案尚不可裁断。")
        state = self.db.row("SELECT * FROM game_state WHERE id = 1") or {"turn": 1}
        turn = int(state["turn"])
        with self.db.conn:
            treasury_gain = 12 if judgment in {"追银", "下狱追银", "抄没追赃"} else 6
            self.db.change_metric("国库", treasury_gain, high=999)
            self.db.change_metric("君威", 6)
            self.db.change_metric("民心", 2)
            self.db.change_siege("defender_will", 5)
            self.db.change_issue("investigate_pay", 22)
            self.db.change_issue("discipline_guards", 12)
            self.db.conn.execute(
                "UPDATE factions SET fear = ?, backlash = ?, affinity = ? WHERE id = 'transport_tax_network'",
                (clamp(14 + 24), clamp(42 + 9), clamp(35 - 8)),
            )
            self.db.change_faction_clock("transport_slowdown", 15)
            self.db.conn.execute("UPDATE factions SET fear = fear + 8 WHERE id = 'old_party_clients'")
            result = f"裁断：{judgment}。转运判官伏罪，追银入库，禁军欠饷案初定；转运财税网络恐惧上升，也开始暗中抱团。"
            self.db.conn.execute("UPDATE court_cases SET status = 'judged', result = ? WHERE id = ?", (result, case_id))
            self.db.conn.execute("UPDATE evidence_items SET status = 'used' WHERE id IN ('dongcang副册')")
            self.db.conn.execute(
                """INSERT INTO economy_ledger
                   (turn, account, delta, balance_after, category, reason, source, visibility)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (turn, "国库", treasury_gain, self.db.value("国库"), "追赃", "禁军欠饷截留案追银", "殿前对质", "公开"),
            )
            self.db.conn.execute(
                """INSERT INTO memories
                   (subject_type, subject_id, turn, title, cause, process, outcome, sentiment, importance, tags)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    "case",
                    case_id,
                    turn,
                    "禁军欠饷案殿前裁断",
                    "东仓副册显示军饷截留",
                    "皇帝出示账册，质询转运判官与户部主事。",
                    result,
                    "positive",
                    5,
                    json.dumps(["殿前对质", "追赃", "转运财税网络"], ensure_ascii=False),
                ),
            )
        return {"case": self.db.row("SELECT * FROM court_cases WHERE id = ?", (case_id,)), "state": self.state()}
