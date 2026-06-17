from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Iterable

from .content import DATA_DIR, DEFAULT_DB_PATH, GameContent


def clamp(value: int, low: int = 0, high: int = 100) -> int:
    return max(low, min(high, int(value)))


class GameDB:
    def __init__(self, path: Path | str = DEFAULT_DB_PATH):
        self.path = Path(path)
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.init_schema()

    def close(self) -> None:
        self.conn.close()

    def init_schema(self) -> None:
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS game_state (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                year_label TEXT NOT NULL,
                month_label TEXT NOT NULL,
                turn INTEGER NOT NULL,
                phase TEXT NOT NULL,
                ended INTEGER NOT NULL DEFAULT 0,
                ending TEXT NOT NULL DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS metrics (
                key TEXT PRIMARY KEY,
                value INTEGER NOT NULL,
                last_delta INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS characters (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                office TEXT NOT NULL,
                group_name TEXT NOT NULL,
                stance TEXT NOT NULL,
                loyalty INTEGER NOT NULL,
                ability INTEGER NOT NULL,
                integrity INTEGER NOT NULL,
                courage INTEGER NOT NULL,
                prestige INTEGER NOT NULL,
                status TEXT NOT NULL,
                summary TEXT NOT NULL,
                skill TEXT NOT NULL,
                portrait TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS factions (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                influence INTEGER NOT NULL,
                affinity INTEGER NOT NULL,
                damage INTEGER NOT NULL,
                backlash INTEGER NOT NULL,
                fear INTEGER NOT NULL,
                summary TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS faction_clocks (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                faction_id TEXT NOT NULL,
                value INTEGER NOT NULL,
                stage INTEGER NOT NULL,
                trigger TEXT NOT NULL,
                effect TEXT NOT NULL,
                mitigation TEXT NOT NULL,
                status TEXT NOT NULL,
                last_delta INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS regions (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                kind TEXT NOT NULL,
                control INTEGER NOT NULL,
                public_support INTEGER NOT NULL,
                unrest INTEGER NOT NULL,
                tax_capacity INTEGER NOT NULL,
                remittance_rate INTEGER NOT NULL,
                grain_stock INTEGER NOT NULL,
                military_pressure INTEGER NOT NULL,
                route_risk INTEGER NOT NULL,
                gentry_resistance INTEGER NOT NULL,
                x REAL NOT NULL,
                y REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS armies (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                commander TEXT NOT NULL,
                location TEXT NOT NULL,
                manpower INTEGER NOT NULL,
                morale INTEGER NOT NULL,
                training INTEGER NOT NULL,
                equipment INTEGER NOT NULL,
                supply INTEGER NOT NULL,
                arrears INTEGER NOT NULL,
                loyalty INTEGER NOT NULL,
                mobility INTEGER NOT NULL,
                stance TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS siege_state (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                city_defense INTEGER NOT NULL,
                defender_will INTEGER NOT NULL,
                gate_risk INTEGER NOT NULL,
                fire_risk INTEGER NOT NULL,
                peace_pressure INTEGER NOT NULL,
                jin_pressure INTEGER NOT NULL,
                qinwang_response INTEGER NOT NULL,
                grain_price INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS diplomacy_state (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                demand_severity INTEGER NOT NULL,
                trust INTEGER NOT NULL,
                impatience INTEGER NOT NULL,
                internal_tension INTEGER NOT NULL,
                leverage INTEGER NOT NULL,
                current_demand TEXT NOT NULL,
                status TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS logistics_routes (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                origin TEXT NOT NULL,
                destination TEXT NOT NULL,
                capacity INTEGER NOT NULL,
                risk INTEGER NOT NULL,
                delay INTEGER NOT NULL,
                controller TEXT NOT NULL,
                corruption INTEGER NOT NULL,
                escort INTEGER NOT NULL,
                status TEXT NOT NULL,
                eta INTEGER NOT NULL,
                current_load INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS city_gates (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                condition INTEGER NOT NULL,
                garrison INTEGER NOT NULL,
                commander TEXT NOT NULL,
                risk INTEGER NOT NULL,
                equipment INTEGER NOT NULL,
                x REAL NOT NULL,
                y REAL NOT NULL,
                status TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS events (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                kind TEXT NOT NULL,
                summary TEXT NOT NULL,
                urgency INTEGER NOT NULL,
                severity INTEGER NOT NULL,
                credibility INTEGER NOT NULL,
                interests TEXT NOT NULL,
                audiences TEXT NOT NULL,
                actions TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'active',
                read INTEGER NOT NULL DEFAULT 0,
                focus INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS issues (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                value INTEGER NOT NULL,
                assignee TEXT NOT NULL,
                status TEXT NOT NULL,
                summary TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS secret_orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                assignee TEXT NOT NULL,
                content TEXT NOT NULL,
                tags TEXT NOT NULL,
                due_turn INTEGER NOT NULL,
                secrecy INTEGER NOT NULL,
                risk INTEGER NOT NULL,
                progress INTEGER NOT NULL,
                status TEXT NOT NULL,
                result TEXT NOT NULL DEFAULT '',
                created_turn INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS evidence_items (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                kind TEXT NOT NULL,
                strength INTEGER NOT NULL,
                reliability INTEGER NOT NULL,
                source TEXT NOT NULL,
                implicated TEXT NOT NULL,
                usable_in_court INTEGER NOT NULL,
                risk_if_revealed TEXT NOT NULL,
                status TEXT NOT NULL,
                created_turn INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS court_cases (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                suspects TEXT NOT NULL,
                evidence_ids TEXT NOT NULL,
                stakes TEXT NOT NULL,
                public_pressure INTEGER NOT NULL,
                risk INTEGER NOT NULL,
                status TEXT NOT NULL,
                result TEXT NOT NULL DEFAULT '',
                created_turn INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS directives (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                text TEXT NOT NULL,
                form TEXT NOT NULL,
                domain TEXT NOT NULL,
                target TEXT NOT NULL,
                assignee TEXT NOT NULL,
                resources TEXT NOT NULL,
                deadline TEXT NOT NULL,
                risk TEXT NOT NULL,
                status TEXT NOT NULL,
                created_turn INTEGER NOT NULL,
                structured_json TEXT NOT NULL DEFAULT '{}',
                result_summary TEXT NOT NULL DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS turn_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                turn INTEGER NOT NULL,
                title TEXT NOT NULL,
                summary TEXT NOT NULL,
                narrative TEXT NOT NULL,
                metrics_delta_json TEXT NOT NULL,
                timeline_json TEXT NOT NULL,
                directives_json TEXT NOT NULL,
                warnings_json TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS battle_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                turn INTEGER NOT NULL,
                title TEXT NOT NULL,
                summary TEXT NOT NULL,
                outcome TEXT NOT NULL,
                reasons_json TEXT NOT NULL,
                losses_json TEXT NOT NULL,
                changes_json TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS court_debates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                turn INTEGER NOT NULL,
                topic TEXT NOT NULL,
                summary TEXT NOT NULL,
                options_json TEXT NOT NULL,
                speakers_json TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS economy_ledger (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                turn INTEGER NOT NULL,
                account TEXT NOT NULL,
                delta INTEGER NOT NULL,
                balance_after INTEGER NOT NULL,
                category TEXT NOT NULL,
                reason TEXT NOT NULL,
                source TEXT NOT NULL,
                visibility TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject_type TEXT NOT NULL,
                subject_id TEXT NOT NULL,
                turn INTEGER NOT NULL,
                title TEXT NOT NULL,
                cause TEXT NOT NULL,
                process TEXT NOT NULL,
                outcome TEXT NOT NULL,
                sentiment TEXT NOT NULL,
                importance INTEGER NOT NULL,
                tags TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            """
        )
        self.conn.commit()

    def reset_seed(self, content: GameContent) -> None:
        tables = [
            "game_state",
            "metrics",
            "characters",
            "factions",
            "faction_clocks",
            "regions",
            "armies",
            "siege_state",
            "city_gates",
            "events",
            "issues",
            "secret_orders",
            "evidence_items",
            "court_cases",
            "directives",
            "turn_reports",
            "battle_reports",
            "court_debates",
            "economy_ledger",
            "memories",
            "logistics_routes",
            "diplomacy_state",
        ]
        with self.conn:
            for table in tables:
                self.conn.execute(f"DELETE FROM {table}")
            self.conn.execute(
                "INSERT INTO game_state (id, year_label, month_label, turn, phase) VALUES (1, ?, ?, ?, ?)",
                ("靖康元年", "正月", 1, "朝报"),
            )
            for key, value in {
                "国库": 42,
                "内帑": 18,
                "京城粮": 31,
                "民心": 62,
                "君威": 48,
            }.items():
                self.conn.execute("INSERT INTO metrics (key, value) VALUES (?, ?)", (key, value))
            self.conn.execute(
                """INSERT INTO siege_state
                   (id, city_defense, defender_will, gate_risk, fire_risk, peace_pressure, jin_pressure, qinwang_response, grain_price)
                   VALUES (1, 42, 45, 38, 22, 36, 54, 18, 124)"""
            )
            self.conn.execute(
                """INSERT INTO diplomacy_state
                   (id, demand_severity, trust, impatience, internal_tension, leverage, current_demand, status)
                   VALUES (1, 48, 32, 54, 26, 22, ?, ?)""",
                ("金营尚未正式入城索约", "未接触"),
            )
            for item in content.logistics_routes:
                self.conn.execute(
                    """INSERT INTO logistics_routes
                       (id, name, origin, destination, capacity, risk, delay, controller, corruption, escort, status, eta, current_load)
                       VALUES (:id, :name, :origin, :destination, :capacity, :risk, :delay, :controller, :corruption, :escort, :status, :eta, :current_load)""",
                    item,
                )
            gates = [
                ("xuanhua_gate", "宣化门", 47, 3000, "待命", 42, 36, 56, 48, "危"),
                ("chenzhou_gate", "陈州门", 52, 2200, "殿前司", 34, 44, 60, 62, "稳"),
                ("xin_song_gate", "新宋门", 44, 1800, "禁军都虞候", 48, 30, 45, 57, "疑"),
                ("bian_river_gate", "汴河水门", 39, 900, "水门巡检", 51, 28, 66, 54, "危"),
                ("granary_quarter", "粮仓区", 58, 600, "开封府", 31, 40, 62, 45, "稳"),
            ]
            self.conn.executemany(
                """INSERT INTO city_gates
                   (id, name, condition, garrison, commander, risk, equipment, x, y, status)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                gates,
            )
            for item in content.characters:
                self.conn.execute(
                    """INSERT INTO characters
                       (id, name, office, group_name, stance, loyalty, ability, integrity, courage, prestige, status, summary, skill, portrait)
                       VALUES (:id, :name, :office, :group_name, :stance, :loyalty, :ability, :integrity, :courage, :prestige, :status, :summary, :skill, :portrait)""",
                    item,
                )
            for item in content.factions:
                self.conn.execute(
                    """INSERT INTO factions
                       (id, name, influence, affinity, damage, backlash, fear, summary)
                       VALUES (:id, :name, :influence, :affinity, :damage, :backlash, :fear, :summary)""",
                    item,
                )
            self.seed_faction_clocks()
            for item in content.regions:
                self.conn.execute(
                    """INSERT INTO regions
                       (id, name, kind, control, public_support, unrest, tax_capacity, remittance_rate, grain_stock, military_pressure, route_risk, gentry_resistance, x, y)
                       VALUES (:id, :name, :kind, :control, :public_support, :unrest, :tax_capacity, :remittance_rate, :grain_stock, :military_pressure, :route_risk, :gentry_resistance, :x, :y)""",
                    item,
                )
            for item in content.armies:
                self.conn.execute(
                    """INSERT INTO armies
                       (id, name, commander, location, manpower, morale, training, equipment, supply, arrears, loyalty, mobility, stance)
                       VALUES (:id, :name, :commander, :location, :manpower, :morale, :training, :equipment, :supply, :arrears, :loyalty, :mobility, :stance)""",
                    item,
                )
            for item in content.events:
                self.conn.execute(
                    """INSERT INTO events
                       (id, title, kind, summary, urgency, severity, credibility, interests, audiences, actions, status, read, focus)
                       VALUES (:id, :title, :kind, :summary, :urgency, :severity, :credibility, :interests, :audiences, :actions, :status, :read, :focus)""",
                    {
                        **item,
                        "interests": json.dumps(item.get("interests", []), ensure_ascii=False),
                        "audiences": json.dumps(item.get("audiences", []), ensure_ascii=False),
                        "actions": json.dumps(item.get("actions", []), ensure_ascii=False),
                    },
                )
            for item in content.issues:
                self.conn.execute(
                    """INSERT INTO issues (id, title, value, assignee, status, summary)
                       VALUES (:id, :title, :value, :assignee, :status, :summary)""",
                    item,
                )

    def rows(self, sql: str, params: Iterable[Any] = ()) -> list[dict[str, Any]]:
        return [dict(row) for row in self.conn.execute(sql, tuple(params)).fetchall()]

    def row(self, sql: str, params: Iterable[Any] = ()) -> dict[str, Any] | None:
        found = self.conn.execute(sql, tuple(params)).fetchone()
        return dict(found) if found else None

    def value(self, key: str) -> int:
        row = self.row("SELECT value FROM metrics WHERE key = ?", (key,))
        if not row:
            raise KeyError(key)
        return int(row["value"])

    def change_metric(self, key: str, delta: int, *, low: int = 0, high: int = 999) -> int:
        current = self.value(key)
        next_value = max(low, min(high, current + int(delta)))
        self.conn.execute("UPDATE metrics SET value = ?, last_delta = ? WHERE key = ?", (next_value, next_value - current, key))
        return next_value

    def change_siege(self, key: str, delta: int, *, low: int = 0, high: int = 100) -> int:
        row = self.row(f"SELECT {key} FROM siege_state WHERE id = 1")
        if not row:
            raise KeyError(key)
        current = int(row[key])
        next_value = max(low, min(high, current + int(delta)))
        self.conn.execute(f"UPDATE siege_state SET {key} = ? WHERE id = 1", (next_value,))
        return next_value

    def change_diplomacy(self, key: str, delta: int, *, low: int = 0, high: int = 100) -> int:
        row = self.row(f"SELECT {key} FROM diplomacy_state WHERE id = 1")
        if not row:
            raise KeyError(key)
        current = int(row[key])
        next_value = max(low, min(high, current + int(delta)))
        self.conn.execute(f"UPDATE diplomacy_state SET {key} = ? WHERE id = 1", (next_value,))
        return next_value

    def set_diplomacy_text(self, *, current_demand: str | None = None, status: str | None = None) -> None:
        updates: dict[str, str] = {}
        if current_demand is not None:
            updates["current_demand"] = current_demand
        if status is not None:
            updates["status"] = status
        if not updates:
            return
        parts = ", ".join(f"{field} = ?" for field in updates)
        self.conn.execute(f"UPDATE diplomacy_state SET {parts} WHERE id = 1", list(updates.values()))

    def change_route(self, route_id: str, changes: dict[str, int | str]) -> dict[str, Any] | None:
        route = self.row("SELECT * FROM logistics_routes WHERE id = ?", (route_id,))
        if not route:
            return None
        next_values: dict[str, int | str] = {}
        for key, delta in changes.items():
            if isinstance(delta, int) and key in {"risk", "corruption", "escort", "eta", "current_load"}:
                low = 0
                high = 100 if key not in {"eta", "current_load"} else 999
                next_values[key] = max(low, min(high, int(route[key]) + delta))
            else:
                next_values[key] = delta
        if next_values:
            parts = ", ".join(f"{field} = ?" for field in next_values)
            self.conn.execute(f"UPDATE logistics_routes SET {parts} WHERE id = ?", [*next_values.values(), route_id])
        return self.row("SELECT * FROM logistics_routes WHERE id = ?", (route_id,))

    def change_issue(self, issue_id: str, delta: int) -> int:
        row = self.row("SELECT value FROM issues WHERE id = ?", (issue_id,))
        if not row:
            return 0
        current = int(row["value"])
        next_value = max(-100, min(100, current + int(delta)))
        self.conn.execute("UPDATE issues SET value = ? WHERE id = ?", (next_value, issue_id))
        return next_value

    def clock_stage(self, value: int) -> int:
        if value >= 85:
            return 5
        if value >= 70:
            return 4
        if value >= 55:
            return 3
        if value >= 40:
            return 2
        if value >= 20:
            return 1
        return 0

    def seed_faction_clocks(self) -> None:
        clocks = [
            {
                "id": "li_gang_removal",
                "title": "罢李纲风波",
                "faction_id": "peace_party",
                "value": 18,
                "trigger": "任李纲过权、守城扰民、战事受挫",
                "effect": "弹劾主战重臣，迫使城防指挥摇摆",
                "mitigation": "公开战报与城防成果，限制主和派借题发挥",
            },
            {
                "id": "transport_slowdown",
                "title": "转运怠工",
                "faction_id": "transport_tax_network",
                "value": 26,
                "trigger": "查账、追赃、低价征粮、开仓平粜",
                "effect": "粮船迟滞、军饷缩水、账册缺页",
                "mitigation": "给脚价、护粮并点名问责关键节点",
            },
            {
                "id": "southern_flight_talk",
                "title": "南迁暗议",
                "faction_id": "inner_court",
                "value": 16,
                "trigger": "金军威压、粮价、城防低、宗室恐惧",
                "effect": "宗室内廷逼宫，君威下降，主和压力上升",
                "mitigation": "稳城防、安内廷、公开守城胜算",
            },
            {
                "id": "western_army_grievance",
                "title": "西军怨望",
                "faction_id": "war_party",
                "value": 22,
                "trigger": "空头赏格、欠饷、文臣掣肘、路线受阻",
                "effect": "勤王迟缓，援军观望或绕路",
                "mitigation": "兑现赏格、派使催促、调粮接应",
            },
            {
                "id": "grain_market_strike",
                "title": "粮行罢市",
                "faction_id": "capital_people",
                "value": 14,
                "trigger": "强买、滥抄、赖账、粮价恐慌",
                "effect": "粮价暴涨，坊市冲突，民心下降",
                "mitigation": "保价收粮、平粜限价并保护正常商户",
            },
        ]
        with self.conn:
            for clock in clocks:
                value = int(clock["value"])
                self.conn.execute(
                    """INSERT INTO faction_clocks
                       (id, title, faction_id, value, stage, trigger, effect, mitigation, status)
                       VALUES (:id, :title, :faction_id, :value, :stage, :trigger, :effect, :mitigation, :status)
                       ON CONFLICT(id) DO NOTHING""",
                    {
                        **clock,
                        "stage": self.clock_stage(value),
                        "status": "active",
                    },
                )

    def change_faction_clock(self, clock_id: str, delta: int) -> dict[str, Any] | None:
        row = self.row("SELECT * FROM faction_clocks WHERE id = ?", (clock_id,))
        if not row:
            return None
        current = int(row["value"])
        next_value = clamp(current + int(delta), 0, 100)
        self.conn.execute(
            "UPDATE faction_clocks SET value = ?, stage = ?, last_delta = ? WHERE id = ?",
            (next_value, self.clock_stage(next_value), next_value - current, clock_id),
        )
        return self.row("SELECT * FROM faction_clocks WHERE id = ?", (clock_id,))

    def upsert_event(self, item: dict[str, Any]) -> None:
        self.conn.execute(
            """INSERT INTO events
               (id, title, kind, summary, urgency, severity, credibility, interests, audiences, actions, status, read, focus)
               VALUES (:id, :title, :kind, :summary, :urgency, :severity, :credibility, :interests, :audiences, :actions, :status, :read, :focus)
               ON CONFLICT(id) DO UPDATE SET
                 title = excluded.title,
                 kind = excluded.kind,
                 summary = excluded.summary,
                 urgency = excluded.urgency,
                 severity = excluded.severity,
                 credibility = excluded.credibility,
                 interests = excluded.interests,
                 audiences = excluded.audiences,
                 actions = excluded.actions,
                 status = excluded.status,
                 focus = excluded.focus""",
            {
                **item,
                "interests": json.dumps(item.get("interests", []), ensure_ascii=False),
                "audiences": json.dumps(item.get("audiences", []), ensure_ascii=False),
                "actions": json.dumps(item.get("actions", []), ensure_ascii=False),
                "status": item.get("status", "active"),
                "read": item.get("read", 0),
                "focus": item.get("focus", 0),
            },
        )

    def create_directive(self, data: dict[str, Any], status: str = "draft") -> dict[str, Any]:
        duplicate = self.row(
            "SELECT * FROM directives WHERE title = ? AND status IN ('draft', 'confirmed')",
            (data["title"],),
        )
        if duplicate:
            return duplicate
        state = self.row("SELECT turn FROM game_state WHERE id = 1") or {"turn": 1}
        with self.conn:
            cur = self.conn.execute(
                """INSERT INTO directives
                   (title, text, form, domain, target, assignee, resources, deadline, risk, status, created_turn, structured_json)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    data["title"],
                    data["text"],
                    data.get("form", "圣旨"),
                    data.get("domain", "军政"),
                    data.get("target", ""),
                    data.get("assignee", ""),
                    data.get("resources", ""),
                    data.get("deadline", "本月"),
                    data.get("risk", "执行偏差"),
                    status,
                    int(state["turn"]),
                    json.dumps(data, ensure_ascii=False),
                ),
            )
        return self.row("SELECT * FROM directives WHERE id = ?", (cur.lastrowid,)) or {}

    def create_secret_order(self, data: dict[str, Any]) -> dict[str, Any]:
        state = self.row("SELECT turn FROM game_state WHERE id = 1") or {"turn": 1}
        with self.conn:
            cur = self.conn.execute(
                """INSERT INTO secret_orders
                   (title, assignee, content, tags, due_turn, secrecy, risk, progress, status, created_turn)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    data["title"],
                    data.get("assignee", "皇城司使"),
                    data.get("content", data["title"]),
                    json.dumps(data.get("tags", []), ensure_ascii=False),
                    int(data.get("due_turn", int(state["turn"]) + 1)),
                    int(data.get("secrecy", 72)),
                    int(data.get("risk", 34)),
                    int(data.get("progress", 0)),
                    data.get("status", "active"),
                    int(state["turn"]),
                ),
            )
        return self.row("SELECT * FROM secret_orders WHERE id = ?", (cur.lastrowid,)) or {}

    def ensure_evidence_and_case(self, turn: int) -> tuple[dict[str, Any], dict[str, Any]]:
        evidence = self.row("SELECT * FROM evidence_items WHERE id = 'dongcang副册'")
        if not evidence:
            self.conn.execute(
                """INSERT INTO evidence_items
                   (id, title, kind, strength, reliability, source, implicated, usable_in_court, risk_if_revealed, status, created_turn)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    "dongcang副册",
                    "东仓副册",
                    "账册",
                    82,
                    76,
                    "皇城司夜查东仓",
                    json.dumps(["转运判官", "户部主事", "转运财税网络"], ensure_ascii=False),
                    1,
                    "公开后会惊动转运财税网络，后续粮船迟滞风险上升。",
                    "new",
                    turn,
                ),
            )
            evidence = self.row("SELECT * FROM evidence_items WHERE id = 'dongcang副册'")
        case = self.row("SELECT * FROM court_cases WHERE id = 'forbidden_army_pay_case'")
        if not case:
            self.conn.execute(
                """INSERT INTO court_cases
                   (id, title, suspects, evidence_ids, stakes, public_pressure, risk, status, created_turn)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    "forbidden_army_pay_case",
                    "禁军欠饷截留案",
                    json.dumps(["转运判官", "户部主事"], ensure_ascii=False),
                    json.dumps(["dongcang副册"], ensure_ascii=False),
                    "禁军军心、户部信用、转运财税网络",
                    64,
                    58,
                    "ready",
                    turn,
                ),
            )
            case = self.row("SELECT * FROM court_cases WHERE id = 'forbidden_army_pay_case'")
        return evidence or {}, case or {}

    def set_setting(self, key: str, value: Any) -> None:
        self.conn.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, json.dumps(value, ensure_ascii=False)),
        )
        self.conn.commit()

    def get_setting(self, key: str, default: Any = None) -> Any:
        row = self.row("SELECT value FROM settings WHERE key = ?", (key,))
        if not row:
            return default
        return json.loads(row["value"])
