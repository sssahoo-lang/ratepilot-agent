"""
agent_graph.py — LangGraph orchestration for the RatePilot negotiation agent.

The negotiation workflow is split into two compiled graphs:

  start_graph   — initial pipeline once a bill is uploaded
                  START -> load_bill -> research -> strategy -> draft_email -> END
                  (ends here; app waits for the provider to reply)

  reply_graph   — processes one provider reply and routes to the correct outcome
                  START -> load_context -> classify_reply -> [accept|counter|escalate|close] -> END

Both graphs share a common NegotiationState TypedDict.  Each node reads what it
needs from state, calls the existing business-logic function from agent_service.py,
writes a step record to the DB, and returns only the keys it updated.
LangGraph merges those keys back into the running state automatically.

Interview one-liner:
  "Each major pipeline stage is a LangGraph node.  The shared state carries bill
   data, research findings, the strategy, and the round count.  A conditional edge
   after reply classification routes to won / counter-offer / close — so the loop
   is expressed in the graph topology rather than nested if-statements."
"""

import asyncio
import json
from datetime import datetime
from typing import Optional

from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END

import aiosqlite

from database import DB_PATH
from agent_service import (
    research_competitors,
    build_strategy,
    draft_negotiation_email,
    interpret_response,
    generate_final_summary,
)


# ── Shared graph state ────────────────────────────────────────────────────────

class NegotiationState(TypedDict, total=False):
    """
    All data that flows between nodes.

    Using total=False so every key is optional — each node only declares and
    returns the keys it touches; LangGraph patches them into the running state.
    """
    # ── identifiers
    negotiation_id: int        # DB primary key for this negotiation
    bill_id: int               # DB primary key for the source bill

    # ── bill context (populated by load_bill_node / load_reply_context_node)
    bill_row: dict             # raw bill row (or negotiation+bill join row)
    bill_data: dict            # parsed extracted_data JSON from the bill
    line_count: int            # number of service lines (1 for individual, N for family)

    # ── pipeline outputs
    research: dict             # output of research_competitors()
    strategy: dict             # output of build_strategy()
    email_draft: dict          # output of draft_negotiation_email()
    round_num: int             # which draft round we are on (1 = first email)

    # ── reply processing (reply_graph only)
    provider_reply: str        # raw text the provider sent back
    history: list              # prior step records fed to interpret_response for context
    interpretation: dict       # output of interpret_response()
    decision: str              # "accept" | "counter" | "escalate" | "close"
    offered_amount: float      # dollar amount extracted from the provider's reply
    savings: float             # computed monthly savings on a won deal

    # ── control flow
    status: str                # current negotiation status (mirrors DB)
    error: Optional[str]       # set by any node that catches an exception


# ── Async DB helpers ──────────────────────────────────────────────────────────
# These mirror the helpers in routers/agent.py but open their own connections
# so each node is self-contained (LangGraph nodes may run in any order).

async def _add_step(
    negotiation_id: int,
    step_type: str,
    content: dict,
    reasoning: str = "",
    decision: str = "",
) -> None:
    """Append one row to negotiation_steps and touch updated_at on the parent."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO negotiation_steps "
            "(negotiation_id, step_type, content, reasoning, decision) "
            "VALUES (?, ?, ?, ?, ?)",
            (negotiation_id, step_type, json.dumps(content), reasoning, decision),
        )
        await db.execute(
            "UPDATE negotiations SET updated_at = ? WHERE id = ?",
            (datetime.now().isoformat(), negotiation_id),
        )
        await db.commit()


async def _update_status(negotiation_id: int, status: str, **kwargs) -> None:
    """Update the negotiation status (and any additional keyword columns)."""
    fields = ["status = ?", "updated_at = ?"]
    values: list = [status, datetime.now().isoformat()]
    for k, v in kwargs.items():
        fields.append(f"{k} = ?")
        values.append(v)
    values.append(negotiation_id)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            f"UPDATE negotiations SET {', '.join(fields)} WHERE id = ?",
            values,
        )
        await db.commit()


# ── Start-pipeline nodes ──────────────────────────────────────────────────────

async def load_bill_node(state: NegotiationState) -> dict:
    """
    Load the bill row from the DB, parse extracted_data, and seed the pipeline state.
    Sets status to 'researching' so the UI shows progress immediately.
    """
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM bills WHERE id = ?", (state["bill_id"],)
            ) as cur:
                row = await cur.fetchone()
        if not row:
            return {"error": f"Bill {state['bill_id']} not found", "status": "failed"}
        bill = dict(row)
        bill_data = json.loads(bill.get("extracted_data") or "{}")
        await _update_status(state["negotiation_id"], "researching")
        return {
            "bill_row":  bill,
            "bill_data": bill_data,
            "line_count": int(bill_data.get("line_count") or 1),
            "status":    "researching",
        }
    except Exception as exc:
        return {"error": str(exc), "status": "failed"}


async def research_node(state: NegotiationState) -> dict:
    """
    Estimate competitor pricing via Claude (wrapped in asyncio.to_thread because
    the Anthropic SDK is synchronous).  Writes the 'research' step to the DB.
    """
    try:
        bill     = state.get("bill_row", {})
        bill_data = state.get("bill_data", {})
        research = await asyncio.to_thread(
            research_competitors,
            bill_data.get("provider", bill.get("provider", "")),
            bill_data.get("bill_type", bill.get("bill_type", "")),
            float(bill.get("current_amount", 0)),
            line_count=state.get("line_count", 1),
        )
        if not research:
            # Fallback values so the pipeline never stalls on an empty LLM response
            current = float(bill.get("current_amount", 0))
            research = {
                "competitor_prices":  [],
                "market_average":     current * 0.8,
                "leverage_points":    ["Long-term customer"],
                "recommended_target": current * 0.75,
                "walkaway_threshold": current * 0.9,
                "research_summary":   "Market research completed.",
            }
        nid = state["negotiation_id"]
        await _add_step(
            nid, "research", research,
            "Estimated competitor pricing",
            f"Market average: ${research.get('market_average', 0):.2f}",
        )
        await _update_status(nid, "strategizing", research_findings=json.dumps(research))
        return {"research": research, "status": "strategizing"}
    except Exception as exc:
        return {"error": str(exc), "status": "failed"}


async def strategy_node(state: NegotiationState) -> dict:
    """
    Build a negotiation strategy (target price, walkaway, key arguments).
    Writes the 'strategy' step and stores it in the negotiations row.
    """
    try:
        strategy = await asyncio.to_thread(
            build_strategy, state.get("bill_data", {}), state.get("research", {})
        )
        if not strategy:
            research = state.get("research", {})
            current  = float((state.get("bill_row") or {}).get("current_amount", 0))
            strategy = {
                "target_price":      research.get("recommended_target", current * 0.8),
                "walkaway_threshold": current * 0.9,
                "primary_leverage":  "Competitor pricing is lower",
                "strategy_summary":  "Leverage competitor pricing.",
            }
        nid = state["negotiation_id"]
        await _add_step(
            nid, "strategy", strategy,
            "Built negotiation strategy",
            f"Target: ${strategy.get('target_price', 0):.2f}",
        )
        await _update_status(
            nid, "drafting",
            target_price=strategy.get("target_price"),
            walkaway_threshold=strategy.get("walkaway_threshold"),
            strategy=json.dumps(strategy),
        )
        return {"strategy": strategy, "status": "drafting"}
    except Exception as exc:
        return {"error": str(exc), "status": "failed"}


async def draft_email_node(state: NegotiationState) -> dict:
    """
    Draft a personalized negotiation email and log it as an 'email_draft' step.
    This is the terminal node in the start pipeline — the app waits here for the
    provider to reply before the reply_graph takes over.
    """
    try:
        round_num  = state.get("round_num", 1) or 1
        email_draft = await asyncio.to_thread(
            draft_negotiation_email,
            state.get("bill_data", {}),
            state.get("research",  {}),
            state.get("strategy",  {}),
            round_num=round_num,
        )
        nid = state["negotiation_id"]
        await _add_step(
            nid, "email_draft", email_draft,
            "Drafted negotiation email",
            f"Asking: ${email_draft.get('ask_amount', 0):.2f}/month",
        )
        await _update_status(nid, "awaiting_reply")
        return {"email_draft": email_draft, "status": "awaiting_reply"}
    except Exception as exc:
        return {"error": str(exc), "status": "failed"}


async def persist_error_node(state: NegotiationState) -> dict:
    """
    Terminal error handler — writes a 'failed' status and an 'error' step so the
    UI can surface the failure with the original error message.
    """
    error = state.get("error", "Unknown error")
    nid   = state.get("negotiation_id")
    if nid:
        try:
            await _update_status(nid, "failed", error_message=error)
            await _add_step(nid, "error", {"error": error},
                            "Pipeline failed at this stage", "failed")
        except Exception:
            pass  # best-effort; don't mask the original error
    return {"status": "failed"}


# ── Reply-pipeline nodes ──────────────────────────────────────────────────────

async def load_reply_context_node(state: NegotiationState) -> dict:
    """
    Load the full negotiation context needed to process a provider reply:
    strategy, research, bill data, and prior step history.
    The history list is passed to interpret_response() as conversation context.
    """
    try:
        nid = state["negotiation_id"]
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT n.*, b.current_amount, b.extracted_data "
                "FROM negotiations n "
                "JOIN bills b ON n.bill_id = b.id "
                "WHERE n.id = ?",
                (nid,),
            ) as cur:
                neg = await cur.fetchone()
            if not neg:
                return {"error": f"Negotiation {nid} not found", "status": "failed"}
            neg = dict(neg)

            async with db.execute(
                "SELECT * FROM negotiation_steps "
                "WHERE negotiation_id = ? ORDER BY created_at",
                (nid,),
            ) as cur:
                steps = [dict(r) for r in await cur.fetchall()]

        strategy  = json.loads(neg.get("strategy")          or "{}")
        bill_data = json.loads(neg.get("extracted_data")    or "{}")
        research  = json.loads(neg.get("research_findings") or "{}")
        round_num = len([s for s in steps if s["step_type"] == "email_draft"]) + 1
        history   = [
            {"type": s["step_type"], "content": (s.get("content") or "")[:200]}
            for s in steps
        ]
        return {
            "bill_row":  neg,       # neg includes current_amount via JOIN
            "bill_data": bill_data,
            "strategy":  strategy,
            "research":  research,
            "history":   history,
            "round_num": round_num,
            "status":    neg.get("status", "awaiting_reply"),
        }
    except Exception as exc:
        return {"error": str(exc), "status": "failed"}


async def classify_reply_node(state: NegotiationState) -> dict:
    """
    The core reply-classification node.

    Calls interpret_response() (which uses Claude to read the provider's reply
    and decide: accept / counter / escalate / close).  Writes a 'reply_received'
    step, updates best_offer_received, and increments rounds_count.
    """
    try:
        nid           = state["negotiation_id"]
        provider_reply = state.get("provider_reply", "")
        strategy       = state.get("strategy", {})
        history        = state.get("history",  [])

        interpretation = await asyncio.to_thread(
            interpret_response, provider_reply, strategy, history
        )
        decision = interpretation.get("decision", "close")
        offered  = float(interpretation.get("offered_amount") or 0)

        await _add_step(
            nid, "reply_received",
            {"reply": provider_reply, "interpretation": interpretation},
            interpretation.get("decision_reasoning", ""),
            interpretation.get("decision", ""),
        )

        # Track best offer and increment round counter in DB
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT best_offer_received, rounds_count FROM negotiations WHERE id = ?",
                (nid,),
            ) as cur:
                row = await cur.fetchone()
        current_best = row["best_offer_received"] if row else None
        rounds       = int((row["rounds_count"] or 0) if row else 0)
        update_kwargs: dict = {"rounds_count": rounds + 1}
        if offered > 0 and (current_best is None or offered < float(current_best)):
            update_kwargs["best_offer_received"] = offered
        await _update_status(nid, state.get("status", "awaiting_reply"), **update_kwargs)

        return {
            "interpretation":  interpretation,
            "decision":        decision,
            "offered_amount":  offered,
        }
    except Exception as exc:
        return {"error": str(exc), "status": "failed"}


async def mark_won_node(state: NegotiationState) -> dict:
    """
    Record a successful deal: compute savings, write 'closed' step,
    generate a plain-English closing summary via Claude.
    """
    try:
        nid     = state["negotiation_id"]
        offered = state.get("offered_amount", 0)
        current = float((state.get("bill_row") or {}).get("current_amount", 0))
        savings = max(0.0, current - offered) if offered > 0 and current > 0 else 0.0

        await _update_status(nid, "won", savings_achieved=savings)
        await _add_step(nid, "closed",
                        {"outcome": "won", "final_amount": offered},
                        "Accepted offer", "DEAL CLOSED")

        summary = await asyncio.to_thread(
            generate_final_summary,
            state.get("bill_data", {}),
            state.get("history",  []),
            "won", savings,
        )
        await _add_step(nid, "summary", {"summary": summary},
                        "Negotiation complete", "WON")
        return {"status": "won", "savings": savings}
    except Exception as exc:
        return {"error": str(exc), "status": "failed"}


async def draft_counter_node(state: NegotiationState) -> dict:
    """
    Draft a counter-offer email and put the negotiation back into
    'awaiting_reply' so the user can send it and wait for the next response.
    The round_num from state ensures Claude knows this is a follow-up round.
    """
    try:
        nid     = state["negotiation_id"]
        counter = await asyncio.to_thread(
            draft_negotiation_email,
            state.get("bill_data",      {}),
            state.get("research",       {}),
            state.get("strategy",       {}),
            round_num=state.get("round_num", 2),
            previous_response=state.get("provider_reply", ""),
        )
        await _add_step(nid, "email_draft", counter,
                        "Counter-offer drafted",
                        f"Counter: ${counter.get('ask_amount', 0):.2f}")
        await _update_status(nid, "awaiting_reply")
        return {"email_draft": counter, "status": "awaiting_reply"}
    except Exception as exc:
        return {"error": str(exc), "status": "failed"}


async def escalate_node(state: NegotiationState) -> dict:
    """Mark the negotiation as escalated for human review."""
    try:
        nid       = state["negotiation_id"]
        reasoning = (state.get("interpretation") or {}).get(
            "decision_reasoning", "Needs human review"
        )
        await _update_status(nid, "escalated")
        await _add_step(nid, "escalated", {"outcome": "escalated"},
                        reasoning, "ESCALATED")
        return {"status": "escalated"}
    except Exception as exc:
        return {"error": str(exc), "status": "failed"}


async def close_no_deal_node(state: NegotiationState) -> dict:
    """
    Close the negotiation without a deal and generate a plain-English
    closing summary explaining why the negotiation ended here.
    """
    try:
        nid = state["negotiation_id"]
        await _update_status(nid, "closed_no_deal")
        await _add_step(nid, "closed", {"outcome": "no_deal"},
                        "Ended without deal", "CLOSED")
        summary = await asyncio.to_thread(
            generate_final_summary,
            state.get("bill_data", {}),
            state.get("history",  []),
            "closed_no_deal", 0,
        )
        await _add_step(nid, "summary", {"summary": summary},
                        "Negotiation complete", "CLOSED")
        return {"status": "closed_no_deal"}
    except Exception as exc:
        return {"error": str(exc), "status": "failed"}


# ── Conditional routing functions ─────────────────────────────────────────────

def _route_after_node(state: NegotiationState) -> str:
    """
    Used after every start-pipeline node.
    If the node set state['error'] (caught an exception), divert to error handler;
    otherwise continue to the next node in sequence.
    """
    return "error" if state.get("error") else "ok"


def _route_reply_decision(state: NegotiationState) -> str:
    """
    The key conditional edge in the reply graph.

    Reads the 'decision' field written by classify_reply_node and routes to:
      accept   -> mark the negotiation won
      counter  -> draft a counter-offer and wait for the next reply
      escalate -> flag for human review
      anything else (close / reject / unknown) -> close without a deal

    An 'error' in state always takes priority over the decision value.
    """
    if state.get("error"):
        return "error"
    decision = (state.get("decision") or "close").lower()
    if decision == "accept":
        return "accept"
    if decision == "counter":
        return "counter"
    if decision == "escalate":
        return "escalate"
    return "close"   # covers "close", "reject", empty string, unknown values


# ── Graph 1: start_graph ──────────────────────────────────────────────────────

def build_start_graph():
    """
    Build and compile the initial negotiation pipeline.

    Topology:
      START -> load_bill -> research -> strategy -> draft_email -> END
                                                                    ^
      Any node may divert to: persist_error -> END  (on exception)

    The graph terminates after draft_email.  The app then waits for the
    provider to reply; reply_graph handles the rest.
    """
    g = StateGraph(NegotiationState)

    g.add_node("load_bill",     load_bill_node)
    g.add_node("research",      research_node)
    g.add_node("strategy",      strategy_node)
    g.add_node("draft_email",   draft_email_node)
    g.add_node("persist_error", persist_error_node)

    g.add_edge(START, "load_bill")

    # Each node: success -> next, exception -> persist_error
    for src, nxt in [
        ("load_bill",  "research"),
        ("research",   "strategy"),
        ("strategy",   "draft_email"),
    ]:
        g.add_conditional_edges(
            src, _route_after_node, {"ok": nxt, "error": "persist_error"}
        )
    g.add_conditional_edges(
        "draft_email", _route_after_node, {"ok": END, "error": "persist_error"}
    )
    g.add_edge("persist_error", END)

    return g.compile()


# ── Graph 2: reply_graph ──────────────────────────────────────────────────────

def build_reply_graph():
    """
    Build and compile the reply-processing graph.

    Topology:
      START -> load_context -> classify_reply
                                   |-- accept   -> mark_won       -> END
                                   |-- counter  -> draft_counter  -> END
                                   |-- escalate -> escalate       -> END
                                   |-- close/*  -> close_no_deal  -> END
                                   |-- error    -> persist_error  -> END
              (load_context error also diverts to persist_error -> END)

    The conditional edge after classify_reply is where LangGraph earns its keep:
    instead of nested if-statements in a route handler, the branching is declared
    in the graph topology and inspectable via start_graph.get_graph().
    """
    g = StateGraph(NegotiationState)

    g.add_node("load_context",   load_reply_context_node)
    g.add_node("classify_reply", classify_reply_node)
    g.add_node("mark_won",       mark_won_node)
    g.add_node("draft_counter",  draft_counter_node)
    g.add_node("escalate",       escalate_node)
    g.add_node("close_no_deal",  close_no_deal_node)
    g.add_node("persist_error",  persist_error_node)

    g.add_edge(START, "load_context")
    g.add_conditional_edges(
        "load_context", _route_after_node,
        {"ok": "classify_reply", "error": "persist_error"},
    )
    g.add_conditional_edges(
        "classify_reply", _route_reply_decision,
        {
            "accept":   "mark_won",
            "counter":  "draft_counter",
            "escalate": "escalate",
            "close":    "close_no_deal",
            "error":    "persist_error",
        },
    )
    for terminal in ("mark_won", "draft_counter", "escalate",
                     "close_no_deal", "persist_error"):
        g.add_edge(terminal, END)

    return g.compile()


# ── Module-level compiled singletons ─────────────────────────────────────────
# Import these in routers/agent.py:
#   from agent_graph import start_graph, reply_graph

start_graph = build_start_graph()
reply_graph = build_reply_graph()
