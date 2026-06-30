# Interview Answer — LangGraph in RatePilot

_Use this as a talking-points guide, not a script.  Speak naturally._

---

## The one-sentence version

> "I refactored RatePilot's negotiation pipeline from a single monolithic async function
> into two LangGraph state graphs — one for starting a negotiation and one for processing
> provider replies — so each step is an explicit node with typed state, conditional
> routing, and isolated error handling."

---

## Why LangGraph?

The original pipeline was one long `async def run_pipeline()` function with nested
`try/except` blocks and manual status updates scattered throughout.  It worked, but:

- **Hard to test** — the whole pipeline had to run to test any one step.
- **Hard to extend** — adding a new step (e.g., an approval gate) meant editing
  one large function and manually threading state between steps.
- **Opaque failure modes** — an error in step 3 of 5 was logged but there was no
  structural guarantee the later steps wouldn't run.

LangGraph gives each step an explicit identity (node), typed inputs/outputs (state),
and declarative routing — the topology of the pipeline is visible in code.

---

## What I built

**Two compiled `StateGraph` instances:**

1. **`start_graph`** — runs when a user starts a negotiation:
   ```
   load_bill → research → strategy → draft_email
        ↘         ↘          ↘           ↘
                         persist_error (any error)
   ```

2. **`reply_graph`** — runs when a provider reply is submitted:
   ```
   load_context → classify_reply → mark_won       (accept)
                              → draft_counter   (counter)
                              → escalate        (escalate)
                              → close_no_deal   (close / unknown)
                              → persist_error   (any error)
   ```

**`NegotiationState`** is a `TypedDict` with `total=False` (all keys optional).
State is additive — each node merges its output keys into the running state dict,
which LangGraph threads forward automatically.

---

## How routing works

```python
def _route_after_node(state: NegotiationState) -> str:
    return "error" if state.get("error") else "ok"

def _route_reply_decision(state: NegotiationState) -> str:
    if state.get("error"):
        return "error"
    decision = (state.get("decision") or "close").lower()
    if decision == "accept":   return "accept"
    if decision == "counter":  return "counter"
    if decision == "escalate": return "escalate"
    return "close"
```

Every node in `start_graph` has both `"ok"` and `"error"` edges defined.
`classify_reply` in `reply_graph` uses `_route_reply_decision`.
Unknown decision values default to `"close"` — the safe, conservative choice.

---

## Error handling design

Each node wraps its body in `try/except Exception`.  On any error, the node sets
`state["error"] = str(e)` and returns.  The routing function sees the truthy error
and diverts to `persist_error_node`, which writes the message to the DB and sets
`status = "failed"`.

**The contract:** no exception ever escapes a node into the LangGraph runtime or
the FastAPI background task.  Failures are always surfaced in the database.

---

## Integration with FastAPI

The routes are now thin wrappers:

```python
# start
await start_graph.ainvoke({"negotiation_id": neg_id, "bill_id": bill_id, "round_num": 1})

# reply
final_state = await reply_graph.ainvoke({"negotiation_id": neg_id, "provider_reply": text})
return {"interpretation": final_state["interpretation"], "decision": final_state["decision"]}
```

The frontend API contract (request/response shapes) is unchanged.  LangGraph is purely
an internal orchestration detail.

---

## How I kept it testable

- **Routing functions are pure** — no I/O, trivially unit-testable.
- **Nodes are async functions** — can be called directly with a mocked state dict.
- **All I/O is patchable** — `aiosqlite.connect`, `research_competitors`,
  `draft_negotiation_email`, `interpret_response` are all top-level names that
  `unittest.mock.patch` can replace.
- **`evals/test_langgraph.py`** covers: graph compilation, routing logic,
  individual node behavior, and full end-to-end runs with all I/O mocked.

---

## Trade-offs I'd mention

| What I chose | Alternative | Why I chose it |
|---|---|---|
| Two separate graphs | One graph with branching on `started` vs `replied` | Cleaner separation; each graph has a single entry point and clear purpose |
| `total=False` TypedDict | Separate state classes per graph | Avoids duplicate field definitions; nodes only read the keys they need |
| Per-node DB connections | Shared connection passed through state | aiosqlite connections aren't safe to share across async boundaries |
| Module-level singletons (`start_graph`, `reply_graph`) | Factory call in router | Graphs compile once at import time; compilation includes validation |

---

## What I'd add with more time

- **Checkpointing** — LangGraph supports persisting state between steps so a
  multi-hour negotiation can resume after a server restart.
- **Human-in-the-loop** pause nodes — LangGraph's `interrupt_before` / `interrupt_after`
  would let a user review and edit the draft email before it's sent, without
  breaking the graph structure.
- **Streaming** — `astream_events()` would let the frontend show live progress
  as each node completes rather than polling for status.
