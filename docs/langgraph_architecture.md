# RatePilot — LangGraph Agent Architecture

## Overview

The negotiation agent pipeline is orchestrated with **LangGraph**, a graph-based
framework for stateful, multi-step LLM workflows.  Two compiled graphs replace the
single monolithic `run_pipeline()` function that previously existed in `agent_service.py`.

```
User uploads bill
       │
       ▼
 POST /api/agent/start
       │
       └─► [background task] start_graph.ainvoke()
                │
                ▼
          load_bill ──► research ──► strategy ──► draft_email
                │           │           │              │
             (error)     (error)     (error)        status =
                └───────────┴───────────┴──► persist_error
                                                       │
                                                  status = failed

                                         (email stored → user marks sent)
                                                       │
                                                       ▼
                                           POST /api/agent/simulate-reply
                                                       │
                                                       └─► reply_graph.ainvoke()
                                                               │
                                                               ▼
                                                         load_context
                                                               │
                                                         classify_reply
                                                               │
                                            ┌──────────────────┼─────────────────┐
                                         accept            counter/escalate     close
                                            │                   │                 │
                                         mark_won          draft_counter/      close_no_deal
                                                           escalate
```

## Graphs

### `start_graph` — Initial negotiation pipeline

| Node | Responsibility |
|------|----------------|
| `load_bill` | Fetch bill + negotiation rows from DB; parse `extracted_data` JSON |
| `research` | Call `research_competitors()` via `asyncio.to_thread`; store findings in DB |
| `strategy` | Call `build_strategy()`; store strategy JSON in DB |
| `draft_email` | Call `draft_negotiation_email()`; store email draft + step in DB |
| `persist_error` | Write error message to DB; set `status = "failed"` |

Entry point: `load_bill`  
Terminal nodes: `draft_email` (success), `persist_error` (any error)

### `reply_graph` — Provider reply classification pipeline

| Node | Responsibility |
|------|----------------|
| `load_context` | Re-fetch negotiation row, strategy, research, and message history |
| `classify_reply` | Call `interpret_response()`; update `best_offer_received` + round count |
| `mark_won` | Record savings, call `generate_final_summary()`, set `status = "won"` |
| `draft_counter` | Draft a counter-offer email; set `status = "awaiting_reply"` |
| `escalate` | Flag for human review; set `status = "escalated"` |
| `close_no_deal` | Record outcome + summary; set `status = "closed_no_deal"` |
| `persist_error` | Shared with start_graph; write error + set `status = "failed"` |

Entry point: `load_context`

## State

Both graphs share the same `NegotiationState` TypedDict (`total=False` — all keys optional):

```python
class NegotiationState(TypedDict, total=False):
    negotiation_id: int
    bill_id: int
    bill_row: dict
    bill_data: dict
    line_count: int
    research: dict
    strategy: dict
    email_draft: dict
    round_num: int
    provider_reply: str
    history: list
    interpretation: dict
    decision: str
    offered_amount: float
    savings: float
    status: str
    error: Optional[str]
```

State flows forward through the graph; each node merges its output into state.

## Routing

Two conditional edge functions determine next-node selection:

### `_route_after_node(state) → "ok" | "error"`

Used after every node in `start_graph`.  
Returns `"error"` if `state["error"]` is truthy; otherwise `"ok"`.  
Both edges are defined on each node so any exception anywhere diverts to `persist_error`.

### `_route_reply_decision(state) → "accept" | "counter" | "escalate" | "close" | "error"`

Used after `classify_reply` in `reply_graph`.  
Reads `state["decision"]` and maps it to the appropriate terminal node.  
Unknown values default to `"close"` (safe, conservative).  
`"error"` takes priority over any decision value.

## Error handling

- Every node wraps its work in `try/except Exception`.
- On exception, the node sets `state["error"] = str(e)` and returns.
- `_route_after_node` detects the truthy error and routes to `persist_error_node`.
- `persist_error_node` writes the error to the DB and sets `status = "failed"`.
- The graph terminates cleanly — no unhandled exceptions escape to FastAPI.

## Database access

Each node opens its own `aiosqlite` connection independently.  This avoids sharing
connection objects across async boundaries (a common pitfall with aiosqlite) and keeps
each node self-contained.

## Module layout

```
billfight-agent/
├── agent_graph.py          # LangGraph graphs, nodes, routing — all orchestration logic
├── agent_service.py        # Pure LLM functions: research_competitors, build_strategy,
│                           #   draft_negotiation_email, interpret_response,
│                           #   generate_final_summary
├── routers/
│   └── agent.py            # FastAPI routes — thin wrappers that call ainvoke()
└── evals/
    └── test_langgraph.py   # Unit tests: graph compilation, routing, nodes, full-run
```
