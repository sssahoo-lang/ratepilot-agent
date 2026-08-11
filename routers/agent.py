"""
routers/agent.py — FastAPI routes for agent actions.

Orchestration is now delegated to two LangGraph compiled graphs imported from
agent_graph.py.  The route inputs and outputs are unchanged so the frontend
continues to work without modification.

  POST /api/agent/start          -> launches start_graph as a background task
  POST /api/agent/retry          -> re-launches start_graph for a failed negotiation
  POST /api/agent/simulate-reply -> runs reply_graph and returns decision + interpretation
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
import aiosqlite
from datetime import datetime
from database import DB_PATH

# LangGraph compiled graphs — all orchestration logic lives here
from agent_graph import start_graph, reply_graph

router = APIRouter()


# ── Request models ────────────────────────────────────────────────────────────

class StartNegotiationRequest(BaseModel):
    bill_id: int

class SimulateReplyRequest(BaseModel):
    negotiation_id: int
    reply_text: str

class RetryNegotiationRequest(BaseModel):
    negotiation_id: int


# ── Background task ───────────────────────────────────────────────────────────

async def run_pipeline(bill_id: int, negotiation_id: int) -> None:
    """
    Background task: run the start negotiation graph.

    start_graph covers:  load_bill -> research -> strategy -> draft_email
    Any exception inside a node is caught by the node itself and routed to
    persist_error_node, so this coroutine never raises.
    """
    await start_graph.ainvoke({
        "negotiation_id": negotiation_id,
        "bill_id":        bill_id,
        "round_num":      1,
    })


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/start")
async def start_negotiation(
    request: StartNegotiationRequest,
    background_tasks: BackgroundTasks,
):
    """Create a negotiation row and queue the LangGraph pipeline as a background task."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT id FROM bills WHERE id = ?", (request.bill_id,)
        ) as cursor:
            if not await cursor.fetchone():
                raise HTTPException(404, "Bill not found")
        cursor = await db.execute(
            "INSERT INTO negotiations (bill_id, status) VALUES (?, 'starting')",
            (request.bill_id,),
        )
        negotiation_id = cursor.lastrowid
        await db.commit()

    background_tasks.add_task(run_pipeline, request.bill_id, negotiation_id)
    return {"negotiation_id": negotiation_id, "status": "started"}


@router.post("/retry")
async def retry_negotiation(
    request: RetryNegotiationRequest,
    background_tasks: BackgroundTasks,
):
    """Re-run start_graph for a negotiation that previously failed."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM negotiations WHERE id = ?", (request.negotiation_id,)
        ) as cursor:
            negotiation = await cursor.fetchone()
            if not negotiation:
                raise HTTPException(404, "Not found")
            negotiation = dict(negotiation)

        if negotiation.get("status") != "failed":
            raise HTTPException(400, "Only failed negotiations can be retried")

        await db.execute(
            "UPDATE negotiations SET status = 'starting', error_message = NULL, "
            "updated_at = ? WHERE id = ?",
            (datetime.now().isoformat(), request.negotiation_id),
        )
        await db.commit()

    background_tasks.add_task(
        run_pipeline, negotiation["bill_id"], request.negotiation_id
    )
    return {"negotiation_id": request.negotiation_id, "status": "restarted"}


@router.post("/simulate-reply")
async def simulate_reply(request: SimulateReplyRequest):
    """
    Process a provider reply through reply_graph and return the agent's decision.

    reply_graph covers:
      load_context -> classify_reply -> [mark_won | draft_counter | escalate | close_no_deal]

    The frontend receives the same {interpretation, decision} shape as before.
    """
    # Quick existence check before running the graph
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT id FROM negotiations WHERE id = ?", (request.negotiation_id,)
        ) as cursor:
            if not await cursor.fetchone():
                raise HTTPException(404, "Not found")

    final_state = await reply_graph.ainvoke({
        "negotiation_id": request.negotiation_id,
        "provider_reply": request.reply_text,
    })

    return {
        "interpretation": final_state.get("interpretation", {}),
        "decision":       final_state.get("decision", "close"),
    }
