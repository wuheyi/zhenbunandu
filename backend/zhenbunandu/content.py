from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[2]
CONTENT_DIR = ROOT_DIR / "content"
DATA_DIR = ROOT_DIR / "data"
DEFAULT_DB_PATH = DATA_DIR / "game.db"


def load_json(name: str) -> list[dict[str, Any]]:
    path = CONTENT_DIR / name
    with path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, list):
        raise ValueError(f"{name} must contain a JSON list")
    return data


@dataclass(frozen=True)
class GameContent:
    characters: list[dict[str, Any]]
    factions: list[dict[str, Any]]
    regions: list[dict[str, Any]]
    armies: list[dict[str, Any]]
    events: list[dict[str, Any]]
    issues: list[dict[str, Any]]
    directive_templates: list[dict[str, Any]]
    logistics_routes: list[dict[str, Any]]
    historical_anchors: list[dict[str, Any]]


def load_content() -> GameContent:
    return GameContent(
        characters=load_json("characters.json"),
        factions=load_json("factions.json"),
        regions=load_json("regions.json"),
        armies=load_json("armies.json"),
        events=load_json("events.json"),
        issues=load_json("issues.json"),
        directive_templates=load_json("directive_templates.json"),
        logistics_routes=load_json("logistics_routes.json"),
        historical_anchors=load_json("historical_anchors.json"),
    )
