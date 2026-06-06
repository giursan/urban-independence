import os

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from agent import Orchestrator, Store
from agent.config import ElderProfile

load_dotenv()

app = FastAPI(title="Urban Independence — HK Elder Decision Coach")
store = Store(path=os.environ.get("SESSIONS_DB_PATH", "data/sessions.db"))
orchestrator = Orchestrator(store=store)


class StartReq(BaseModel):
    elder_id: str
    name: str = "Friend"
    age: int | None = None
    home_district: str = "Sham Shui Po"
    mobility: str = "walks independently with a cane"
    health_notes: list[str] = []
    languages: list[str] = ["English", "Cantonese"]


class StartResp(BaseModel):
    session_id: str
    scenario_text: str
    scenario: dict
    context: dict


class TurnReq(BaseModel):
    session_id: str
    message: str


class TurnResp(BaseModel):
    reply: str


@app.post("/sessions", response_model=StartResp)
def start_session(req: StartReq) -> StartResp:
    profile = ElderProfile(**req.model_dump())
    session = orchestrator.start_session(profile)
    return StartResp(
        session_id=session.id,
        scenario_text=_format_scenario(session.scenario),
        scenario=session.scenario.model_dump(),
        context=session.context,
    )


@app.post("/sessions/turn", response_model=TurnResp)
def turn(req: TurnReq) -> TurnResp:
    try:
        reply = orchestrator.turn(req.session_id, req.message)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return TurnResp(reply=reply)


@app.post("/sessions/{session_id}/end")
def end_session(session_id: str, summary: str | None = None) -> dict:
    orchestrator.end_session(session_id, summary=summary)
    return {"ok": True}


@app.get("/sessions/{session_id}")
def get_session(session_id: str) -> dict:
    s = store.get_session(session_id)
    if not s:
        raise HTTPException(status_code=404, detail="session not found")
    s["turns"] = store.get_turns(session_id)
    return s


@app.get("/elders/{elder_id}/sessions")
def list_sessions(elder_id: str, limit: int = 50) -> list[dict]:
    return store.list_sessions(elder_id=elder_id, limit=limit)


@app.get("/health")
def health() -> dict:
    return {"ok": True}


def _format_scenario(scenario) -> str:
    opts = "\n".join(f"  ({o.label}) {o.text}" for o in scenario.options)
    return f"{scenario.setting}\n\n{scenario.goal}\n\n{opts}"
