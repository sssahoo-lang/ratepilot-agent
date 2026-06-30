"""
evals/test_langgraph.py — Tests for the LangGraph negotiation agent refactor.

No real API keys required.  Tests cover:
  1. Graph compilation (both graphs build without errors)
  2. _route_after_node   — continues on success, diverts on error
  3. _route_reply_decision — maps every decision value to the correct node
  4. Node-level unit tests with mocked DB and mocked Anthropic calls
  5. Full graph invocation with all I/O mocked (proves the graph topology works)

Run:
  pip install pytest pytest-asyncio
  pytest evals/test_langgraph.py -v
"""

import asyncio
import json
import sys
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Put repo root on path so imports work from either the repo root or evals/
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from agent_graph import (
    NegotiationState,
    _route_after_node,
    _route_reply_decision,
    build_start_graph,
    build_reply_graph,
    start_graph,
    reply_graph,
    load_bill_node,
    research_node,
    strategy_node,
    draft_email_node,
    classify_reply_node,
    mark_won_node,
    draft_counter_node,
    close_no_deal_node,
    escalate_node,
)


# ── helpers ───────────────────────────────────────────────────────────────────

def _mock_aiosqlite(fetchone_result=None, fetchall_result=None):
    """
    Return a mock for aiosqlite.connect that behaves like an async context manager
    and whose cursor returns the given fetchone / fetchall results.
    """
    mock_cursor = MagicMock()
    mock_cursor.__aenter__ = AsyncMock(return_value=mock_cursor)
    mock_cursor.__aexit__ = AsyncMock(return_value=False)
    mock_cursor.fetchone  = AsyncMock(return_value=fetchone_result)
    mock_cursor.fetchall  = AsyncMock(return_value=fetchall_result or [])
    mock_cursor.lastrowid = 42

    mock_db = MagicMock()
    mock_db.__aenter__ = AsyncMock(return_value=mock_db)
    mock_db.__aexit__  = AsyncMock(return_value=False)
    mock_db.commit     = AsyncMock()
    # aiosqlite's db.execute(...) returns an object usable as both
    # `await db.execute(...)` and `async with db.execute(...) as cursor`.
    # MagicMock (not AsyncMock) so calling it returns mock_cursor synchronously;
    # mock_cursor itself is awaitable via __aenter__ when used as a context manager,
    # and execute() is also directly awaitable by giving it an __await__.
    async def _await_cursor():
        return mock_cursor
    def _execute(*args, **kwargs):
        m = MagicMock()
        m.__aenter__ = AsyncMock(return_value=mock_cursor)
        m.__aexit__  = AsyncMock(return_value=False)
        m.__await__  = lambda: _await_cursor().__await__()
        return m
    mock_db.execute     = MagicMock(side_effect=_execute)
    mock_db.row_factory = None
    return mock_db


# ── 1. Graph compilation ──────────────────────────────────────────────────────

def test_start_graph_compiles():
    """start_graph must be a non-None compiled graph with ainvoke."""
    assert start_graph is not None
    assert hasattr(start_graph, "ainvoke")
    assert callable(start_graph.ainvoke)


def test_reply_graph_compiles():
    """reply_graph must be a non-None compiled graph with ainvoke."""
    assert reply_graph is not None
    assert hasattr(reply_graph, "ainvoke")
    assert callable(reply_graph.ainvoke)


def test_graph_factory_functions_return_fresh_graphs():
    """build_* factory functions must each return a distinct compiled graph."""
    g1 = build_start_graph()
    g2 = build_start_graph()
    assert g1 is not g2  # fresh objects each time


def test_start_graph_has_correct_nodes():
    expected = {"load_bill", "research", "strategy", "draft_email", "persist_error"}
    actual   = {n for n in start_graph.get_graph().nodes if not n.startswith("__")}
    assert expected == actual, f"Unexpected nodes: {actual ^ expected}"


def test_reply_graph_has_correct_nodes():
    expected = {
        "load_context", "classify_reply",
        "mark_won", "draft_counter", "escalate", "close_no_deal", "persist_error",
    }
    actual = {n for n in reply_graph.get_graph().nodes if not n.startswith("__")}
    assert expected == actual, f"Unexpected nodes: {actual ^ expected}"


# ── 2. _route_after_node ──────────────────────────────────────────────────────

def test_route_continues_when_no_error():
    assert _route_after_node({})                      == "ok"
    assert _route_after_node({"error": None})         == "ok"
    assert _route_after_node({"negotiation_id": 1})   == "ok"


def test_route_diverts_on_truthy_error():
    assert _route_after_node({"error": "DB down"})    == "error"
    assert _route_after_node({"error": "boom"})       == "error"


def test_route_treats_empty_string_error_as_ok():
    # An empty string is falsy; only truthy error messages divert.
    assert _route_after_node({"error": ""}) == "ok"


# ── 3. _route_reply_decision ──────────────────────────────────────────────────

@pytest.mark.parametrize("decision,expected_route", [
    ("accept",       "accept"),
    ("counter",      "counter"),
    ("escalate",     "escalate"),
    ("close",        "close"),
    ("reject",       "close"),    # unrecognized → safe default
    ("stalling",     "close"),
    ("",             "close"),
])
def test_route_reply_all_decisions(decision, expected_route):
    assert _route_reply_decision({"decision": decision}) == expected_route


def test_route_reply_no_decision_defaults_close():
    assert _route_reply_decision({}) == "close"


def test_route_reply_error_overrides_accept():
    """An error in state must take priority over a valid decision."""
    assert _route_reply_decision({"decision": "accept", "error": "DB failed"}) == "error"


def test_route_reply_error_overrides_counter():
    assert _route_reply_decision({"decision": "counter", "error": "timeout"}) == "error"


# ── 4. Individual node unit tests ─────────────────────────────────────────────

def test_load_bill_node_returns_error_when_bill_missing():
    """If the DB returns no bill row, load_bill_node must set error in state."""
    mock_db = _mock_aiosqlite(fetchone_result=None)
    with patch("agent_graph.aiosqlite.connect", return_value=mock_db), \
         patch("agent_graph._update_status", new=AsyncMock()):
        result = asyncio.run(
            load_bill_node({"negotiation_id": 1, "bill_id": 99})
        )
    assert result.get("error") is not None
    assert result.get("status") == "failed"


def test_load_bill_node_returns_bill_data_on_success():
    bill_row = {
        "id": 1, "provider": "AT&T", "bill_type": "internet",
        "current_amount": 100.0,
        "extracted_data": json.dumps({"provider": "AT&T", "line_count": 1}),
    }
    mock_db = _mock_aiosqlite(fetchone_result=bill_row)
    with patch("agent_graph.aiosqlite.connect", return_value=mock_db), \
         patch("agent_graph._update_status", new=AsyncMock()):
        result = asyncio.run(
            load_bill_node({"negotiation_id": 1, "bill_id": 1})
        )
    assert result.get("error") is None
    assert result["bill_data"]["provider"] == "AT&T"
    assert result["line_count"] == 1
    assert result["status"] == "researching"


def test_research_node_uses_fallback_on_empty_llm_response():
    """If research_competitors returns {}, research_node must supply fallback values."""
    bill_row = {"provider": "AT&T", "bill_type": "internet", "current_amount": 100.0}
    state = {
        "negotiation_id": 1,
        "bill_row": bill_row,
        "bill_data": bill_row,
        "line_count": 1,
    }
    with patch("agent_graph.research_competitors", return_value={}), \
         patch("agent_graph._add_step",      new=AsyncMock()), \
         patch("agent_graph._update_status", new=AsyncMock()):
        result = asyncio.run(research_node(state))
    assert result.get("error") is None
    assert result["research"]["market_average"] > 0    # fallback populated
    assert result["status"] == "strategizing"


def test_classify_reply_node_extracts_decision():
    """classify_reply_node must surface the decision and offered_amount from interpret_response."""
    mock_interpretation = {
        "decision": "counter",
        "offered_amount": 85.0,
        "decision_reasoning": "Offer above target, counter.",
        "classification": "partial_offer",
        "confidence": 0.85,
        "summary": "Too high, countering.",
    }
    state = {
        "negotiation_id": 1,
        "provider_reply": "Best we can do is $85.",
        "strategy": {"target_price": 70, "walkaway_threshold": 80},
        "history": [],
        "status": "awaiting_reply",
    }
    row_mock = {"best_offer_received": None, "rounds_count": 0}
    mock_db  = _mock_aiosqlite(fetchone_result=row_mock)
    with patch("agent_graph.interpret_response",  return_value=mock_interpretation), \
         patch("agent_graph.aiosqlite.connect",   return_value=mock_db), \
         patch("agent_graph._add_step",           new=AsyncMock()), \
         patch("agent_graph._update_status",      new=AsyncMock()):
        result = asyncio.run(classify_reply_node(state))
    assert result["decision"]       == "counter"
    assert result["offered_amount"] == 85.0
    assert result.get("error") is None


# ── 5. Full graph invocation with complete mocking ────────────────────────────

MOCK_BILL = {
    "id": 1, "provider": "AT&T", "bill_type": "internet",
    "current_amount": 100.0,
    "extracted_data": json.dumps({"provider": "AT&T", "bill_type": "internet",
                                   "current_amount": 100.0, "line_count": 1}),
}
MOCK_RESEARCH  = {"competitor_prices": [], "market_average": 72.0,
                  "recommended_target": 70.0, "walkaway_threshold": 80.0,
                  "leverage_points": ["Competitors cheaper"], "research_summary": "OK"}
MOCK_STRATEGY  = {"target_price": 70.0, "walkaway_threshold": 80.0,
                  "opening_position": "Ask for $70", "key_arguments": ["comp pricing"]}
MOCK_EMAIL     = {"subject": "Rate request", "body": "Please reduce to $70.",
                  "ask_amount": 70.0, "key_arguments_used": [], "reasoning": "Target"}


def test_start_graph_full_run_produces_expected_keys():
    """
    Run start_graph end-to-end with all external I/O mocked.
    Verifies: graph routes correctly through all 4 nodes without error.
    """
    mock_db = _mock_aiosqlite(fetchone_result=MOCK_BILL)
    with patch("agent_graph.aiosqlite.connect",      return_value=mock_db), \
         patch("agent_graph.research_competitors",   return_value=MOCK_RESEARCH), \
         patch("agent_graph.build_strategy",         return_value=MOCK_STRATEGY), \
         patch("agent_graph.draft_negotiation_email", return_value=MOCK_EMAIL), \
         patch("agent_graph._add_step",              new=AsyncMock()), \
         patch("agent_graph._update_status",         new=AsyncMock()):
        final = asyncio.run(
            start_graph.ainvoke({"negotiation_id": 1, "bill_id": 1, "round_num": 1})
        )
    assert final.get("error") is None,          f"Graph errored: {final.get('error')}"
    assert final.get("research")   == MOCK_RESEARCH
    assert final.get("strategy")   == MOCK_STRATEGY
    assert final.get("email_draft") == MOCK_EMAIL
    assert final.get("status")     == "awaiting_reply"


def test_reply_graph_accept_routes_to_won():
    """
    When classify_reply_node returns decision='accept', the graph must
    route to mark_won_node and set status='won'.
    """
    neg_row = {
        "id": 1, "bill_id": 1, "status": "awaiting_reply",
        "strategy": json.dumps(MOCK_STRATEGY),
        "research_findings": json.dumps(MOCK_RESEARCH),
        "extracted_data": MOCK_BILL["extracted_data"],
        "current_amount": 100.0,
        "best_offer_received": None,
        "rounds_count": 0,
    }
    mock_interp = {
        "decision": "accept", "offered_amount": 70.0,
        "decision_reasoning": "Meets target.", "classification": "accepted",
        "confidence": 0.95, "summary": "Deal done.",
    }
    mock_db = _mock_aiosqlite(fetchone_result=neg_row)
    with patch("agent_graph.aiosqlite.connect",    return_value=mock_db), \
         patch("agent_graph.interpret_response",   return_value=mock_interp), \
         patch("agent_graph.generate_final_summary", return_value="Great outcome."), \
         patch("agent_graph._add_step",            new=AsyncMock()), \
         patch("agent_graph._update_status",       new=AsyncMock()):
        final = asyncio.run(reply_graph.ainvoke({
            "negotiation_id": 1,
            "provider_reply": "We agree to $70/month.",
        }))
    assert final.get("status")   == "won"
    assert final.get("decision") == "accept"
    assert final.get("error") is None


def test_reply_graph_counter_routes_back_to_awaiting():
    """
    When decision='counter', the graph routes to draft_counter_node and
    the negotiation returns to awaiting_reply status.
    """
    neg_row = {
        "id": 1, "bill_id": 1, "status": "awaiting_reply",
        "strategy": json.dumps(MOCK_STRATEGY),
        "research_findings": json.dumps(MOCK_RESEARCH),
        "extracted_data": MOCK_BILL["extracted_data"],
        "current_amount": 100.0,
        "best_offer_received": None,
        "rounds_count": 1,
    }
    mock_interp = {
        "decision": "counter", "offered_amount": 85.0,
        "decision_reasoning": "Above target, push harder.",
        "classification": "partial_offer", "confidence": 0.8,
        "summary": "Counter at $70.",
    }
    mock_counter = {"subject": "Follow-up", "body": "Hold at $70.", "ask_amount": 70.0}
    mock_db = _mock_aiosqlite(fetchone_result=neg_row)
    with patch("agent_graph.aiosqlite.connect",      return_value=mock_db), \
         patch("agent_graph.interpret_response",     return_value=mock_interp), \
         patch("agent_graph.draft_negotiation_email", return_value=mock_counter), \
         patch("agent_graph._add_step",              new=AsyncMock()), \
         patch("agent_graph._update_status",         new=AsyncMock()):
        final = asyncio.run(reply_graph.ainvoke({
            "negotiation_id": 1,
            "provider_reply": "Best we can do is $85/month.",
        }))
    assert final.get("status")     == "awaiting_reply"
    assert final.get("decision")   == "counter"
    assert final.get("email_draft") == mock_counter
    assert final.get("error") is None


def test_reply_graph_close_routes_to_closed_no_deal():
    """
    When decision='close' (or any unrecognized value), the graph routes to
    close_no_deal_node and terminates without a deal.
    """
    neg_row = {
        "id": 1, "bill_id": 1, "status": "awaiting_reply",
        "strategy": json.dumps(MOCK_STRATEGY),
        "research_findings": json.dumps(MOCK_RESEARCH),
        "extracted_data": MOCK_BILL["extracted_data"],
        "current_amount": 100.0,
        "best_offer_received": None,
        "rounds_count": 2,
    }
    mock_interp = {
        "decision": "close", "offered_amount": 0,
        "decision_reasoning": "Flat refusal.", "classification": "rejected",
        "confidence": 0.9, "summary": "No deal.",
    }
    mock_db = _mock_aiosqlite(fetchone_result=neg_row)
    with patch("agent_graph.aiosqlite.connect",      return_value=mock_db), \
         patch("agent_graph.interpret_response",     return_value=mock_interp), \
         patch("agent_graph.generate_final_summary", return_value="No deal reached."), \
         patch("agent_graph._add_step",              new=AsyncMock()), \
         patch("agent_graph._update_status",         new=AsyncMock()):
        final = asyncio.run(reply_graph.ainvoke({
            "negotiation_id": 1,
            "provider_reply": "We cannot offer discounts.",
        }))
    assert final.get("status")  == "closed_no_deal"
    assert final.get("decision") == "close"
    assert final.get("error") is None


def test_reply_graph_escalate_routes_to_escalated():
    """decision='escalate' must route to escalate_node."""
    neg_row = {
        "id": 1, "bill_id": 1, "status": "awaiting_reply",
        "strategy": json.dumps(MOCK_STRATEGY),
        "research_findings": "{}",
        "extracted_data": MOCK_BILL["extracted_data"],
        "current_amount": 100.0,
        "best_offer_received": None,
        "rounds_count": 1,
    }
    mock_interp = {
        "decision": "escalate", "offered_amount": 0,
        "decision_reasoning": "Complex situation needing human review.",
        "classification": "stalling", "confidence": 0.6, "summary": "Escalate.",
    }
    mock_db = _mock_aiosqlite(fetchone_result=neg_row)
    with patch("agent_graph.aiosqlite.connect",  return_value=mock_db), \
         patch("agent_graph.interpret_response", return_value=mock_interp), \
         patch("agent_graph._add_step",          new=AsyncMock()), \
         patch("agent_graph._update_status",     new=AsyncMock()):
        final = asyncio.run(reply_graph.ainvoke({
            "negotiation_id": 1,
            "provider_reply": "We need to review this internally.",
        }))
    assert final.get("status")  == "escalated"
    assert final.get("decision") == "escalate"
    assert final.get("error") is None
