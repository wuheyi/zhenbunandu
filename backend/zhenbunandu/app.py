from __future__ import annotations

import json
from typing import Any, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from .llm import DEFAULT_LLM_BASE_URL, DEFAULT_LLM_MODEL
from .session import GameSession


app = FastAPI(title="朕不南渡 API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

session = GameSession()


class LLMRequest(BaseModel):
    base_url: str = DEFAULT_LLM_BASE_URL
    model: str = DEFAULT_LLM_MODEL
    api_key: str = ""


class ChatRequest(BaseModel):
    message: str = ""


class SecretOrderRequest(BaseModel):
    title: str
    assignee: str = "皇城司使"
    content: str = ""
    tags: list[str] = []
    secrecy: int = 72
    risk: int = 34


class DirectiveRequest(BaseModel):
    title: str = ""
    text: str = ""
    form: str = "圣旨"
    domain: str = "军政"
    target: str = "当前急务"
    assignee: str = "中书门下"
    resources: str = "依实拨付"
    deadline: str = "本月"
    risk: str = "执行偏差"
    status: Optional[str] = None


class JudgmentRequest(BaseModel):
    judgment: str = "追银"


class DebateRequest(BaseModel):
    topic: str = "战和与勤王"


class RouteActionRequest(BaseModel):
    action: str = "escort"


class ClockMitigationRequest(BaseModel):
    action: str = "appease"


class DiplomacyActionRequest(BaseModel):
    action: str = "stall"


def api_error(exc: Exception) -> HTTPException:
    return HTTPException(status_code=400, detail={"message": str(exc)})


@app.get("/api/menu/status")
def menu_status() -> dict[str, Any]:
    return session.menu_status()


@app.post("/api/menu/new_game")
def menu_new_game() -> dict[str, Any]:
    return session.new_game()


@app.post("/api/menu/continue")
def menu_continue() -> dict[str, Any]:
    return session.state()


@app.post("/api/menu/llm")
def menu_llm(request: LLMRequest) -> dict[str, Any]:
    return session.save_llm(request.model_dump())


@app.post("/api/menu/llm/test")
def menu_llm_test() -> dict[str, Any]:
    return session.test_llm()


@app.get("/api/game/state")
def game_state() -> dict[str, Any]:
    return session.state()


@app.post("/api/ministers/{minister_id}/chat")
def minister_chat(minister_id: str, request: ChatRequest) -> dict[str, Any]:
    try:
        return session.minister_chat(minister_id, request.message)
    except Exception as exc:
        raise api_error(exc) from exc


@app.post("/api/court/debate")
def court_debate(request: DebateRequest) -> dict[str, Any]:
    try:
        return session.create_debate(request.topic)
    except Exception as exc:
        raise api_error(exc) from exc


@app.get("/api/secret_orders")
def secret_orders() -> dict[str, Any]:
    return {"orders": session.state()["secret_orders"]}


@app.post("/api/secret_orders")
def create_secret_order(request: SecretOrderRequest) -> dict[str, Any]:
    return session.create_secret_order(request.model_dump())


@app.get("/api/directives")
def directives() -> dict[str, Any]:
    return {"directives": session.state()["directives"]}


@app.post("/api/directives")
def create_directive(request: DirectiveRequest) -> dict[str, Any]:
    return session.create_directive(request.model_dump(exclude_none=True))


@app.patch("/api/directives/{directive_id}")
def patch_directive(directive_id: int, request: DirectiveRequest) -> dict[str, Any]:
    try:
        return session.patch_directive(directive_id, request.model_dump(exclude_none=True))
    except Exception as exc:
        raise api_error(exc) from exc


@app.post("/api/directives/{directive_id}/confirm")
def confirm_directive(directive_id: int) -> dict[str, Any]:
    return session.confirm_directive(directive_id)


@app.post("/api/decree/issue/stream")
def issue_decree_stream() -> StreamingResponse:
    def generate():
        try:
            for item in session.resolve_stream():
                event_name = item["type"]
                payload = {k: v for k, v in item.items() if k != "type"}
                yield f"event: {event_name}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
        except Exception as exc:
            yield f"event: error\ndata: {json.dumps({'message': str(exc)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@app.get("/api/court_cases")
def court_cases() -> dict[str, Any]:
    return {"cases": session.state()["court_cases"], "evidence": session.state()["evidence"]}


@app.post("/api/court_cases/{case_id}/judgment")
def court_case_judgment(case_id: str, request: JudgmentRequest) -> dict[str, Any]:
    try:
        return session.judge_case(case_id, request.judgment)
    except Exception as exc:
        raise api_error(exc) from exc


@app.post("/api/routes/{route_id}/action")
def logistics_route_action(route_id: str, request: RouteActionRequest) -> dict[str, Any]:
    try:
        return session.route_action(route_id, request.action)
    except Exception as exc:
        raise api_error(exc) from exc


@app.post("/api/faction_clocks/{clock_id}/mitigate")
def faction_clock_mitigation(clock_id: str, request: ClockMitigationRequest) -> dict[str, Any]:
    try:
        return session.mitigate_faction_clock(clock_id, request.action)
    except Exception as exc:
        raise api_error(exc) from exc


@app.post("/api/diplomacy/action")
def diplomacy_action(request: DiplomacyActionRequest) -> dict[str, Any]:
    try:
        return session.diplomacy_action(request.action)
    except Exception as exc:
        raise api_error(exc) from exc


@app.get("/api/history/turns")
def history_turns() -> dict[str, Any]:
    return {"reports": session.state()["reports"], "memories": session.state()["memories"]}
