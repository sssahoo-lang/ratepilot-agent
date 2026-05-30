from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
import aiosqlite, json
import time
from datetime import datetime
from database import DB_PATH
from agent_service import research_competitors, build_strategy, draft_negotiation_email, interpret_response, generate_final_summary

router = APIRouter()

class StartNegotiationRequest(BaseModel):
    bill_id: int

class SimulateReplyRequest(BaseModel):
    negotiation_id: int
    reply_text: str

class RetryNegotiationRequest(BaseModel):
    negotiation_id: int

async def add_step(db, nid, stype, content, reasoning="", decision=""):
    await db.execute("INSERT INTO negotiation_steps (negotiation_id, step_type, content, reasoning, decision) VALUES (?, ?, ?, ?, ?)",
                     (nid, stype, json.dumps(content), reasoning, decision))
    await db.execute("UPDATE negotiations SET updated_at = ? WHERE id = ?", (datetime.now().isoformat(), nid))
    await db.commit()

async def update_status(db, nid, status, **kwargs):
    fields, values = ["status = ?", "updated_at = ?"], [status, datetime.now().isoformat()]
    for k, v in kwargs.items(): fields.append(f"{k} = ?"); values.append(v)
    values.append(nid)
    await db.execute(f"UPDATE negotiations SET {', '.join(fields)} WHERE id = ?", values)
    await db.commit()

async def run_pipeline(bill_id, negotiation_id):
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM bills WHERE id = ?", (bill_id,)) as cursor:
                bill_row = await cursor.fetchone()
                if not bill_row: return
                bill = dict(bill_row)
                bill_data = json.loads(bill.get('extracted_data') or '{}')
                line_count = int(bill_data.get("line_count") or 1)
            await update_status(db, negotiation_id, "researching")
            research = research_competitors(bill_data.get('provider', bill['provider']), bill_data.get('bill_type', bill['bill_type']), float(bill['current_amount']), line_count=line_count)
            if not research:
                research = {"competitor_prices": [], "market_average": float(bill['current_amount']) * 0.8, "leverage_points": ["Long-term customer"], "recommended_target": float(bill['current_amount']) * 0.75, "walkaway_threshold": float(bill['current_amount']) * 0.9, "research_summary": "Market research completed."}
            await add_step(db, negotiation_id, "research", research, "Searched competitor pricing", f"Market average: ${research.get('market_average', 0):.2f}")
            time.sleep(2)
            await update_status(db, negotiation_id, "strategizing", research_findings=json.dumps(research))
            strategy = build_strategy(bill_data, research)
            if not strategy:
                strategy = {"target_price": research.get('recommended_target', float(bill['current_amount']) * 0.8), "walkaway_threshold": float(bill['current_amount']) * 0.9, "primary_leverage": "Competitor pricing is lower", "strategy_summary": "Leverage competitor pricing."}
            await add_step(db, negotiation_id, "strategy", strategy, "Built negotiation strategy", f"Target: ${strategy.get('target_price', 0):.2f}")
            time.sleep(2)
            await update_status(db, negotiation_id, "drafting", target_price=strategy.get('target_price'), walkaway_threshold=strategy.get('walkaway_threshold'), strategy=json.dumps(strategy))
            email_draft = draft_negotiation_email(bill_data, research, strategy, round_num=1)
            await add_step(db, negotiation_id, "email_draft", email_draft, "Drafted negotiation email", f"Asking: ${email_draft.get('ask_amount', 0):.2f}/month")
            await update_status(db, negotiation_id, "awaiting_reply")
    except Exception as exc:
        error = str(exc)
        async with aiosqlite.connect(DB_PATH) as db:
            await update_status(db, negotiation_id, "failed", error_message=error)
            await add_step(db, negotiation_id, "error", {"error": error}, "Pipeline failed at this stage", "failed")

@router.post("/start")
async def start_negotiation(request: StartNegotiationRequest, background_tasks: BackgroundTasks):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT id FROM bills WHERE id = ?", (request.bill_id,)) as cursor:
            if not await cursor.fetchone(): raise HTTPException(404, "Bill not found")
        cursor = await db.execute("INSERT INTO negotiations (bill_id, status) VALUES (?, 'starting')", (request.bill_id,))
        negotiation_id = cursor.lastrowid
        await db.commit()
    background_tasks.add_task(run_pipeline, request.bill_id, negotiation_id)
    return {"negotiation_id": negotiation_id, "status": "started"}

@router.post("/retry")
async def retry_negotiation(request: RetryNegotiationRequest, background_tasks: BackgroundTasks):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM negotiations WHERE id = ?", (request.negotiation_id,)) as cursor:
            negotiation = await cursor.fetchone()
            if not negotiation: raise HTTPException(404, "Not found")
            negotiation = dict(negotiation)
        if negotiation.get("status") != "failed":
            raise HTTPException(400, "Only failed negotiations can be retried")
        await db.execute(
            "UPDATE negotiations SET status = 'starting', error_message = NULL, updated_at = ? WHERE id = ?",
            (datetime.now().isoformat(), request.negotiation_id),
        )
        await db.commit()
    background_tasks.add_task(run_pipeline, negotiation["bill_id"], request.negotiation_id)
    return {"negotiation_id": request.negotiation_id, "status": "restarted"}

@router.post("/simulate-reply")
async def simulate_reply(request: SimulateReplyRequest, background_tasks: BackgroundTasks):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT n.*, b.current_amount FROM negotiations n JOIN bills b ON n.bill_id = b.id WHERE n.id = ?",
            (request.negotiation_id,),
        ) as cursor:
            neg = await cursor.fetchone()
            if not neg: raise HTTPException(404, "Not found")
            neg = dict(neg)
        strategy = json.loads(neg.get('strategy') or '{}')
        async with db.execute("SELECT * FROM negotiation_steps WHERE negotiation_id = ? ORDER BY created_at", (request.negotiation_id,)) as cursor:
            steps = [dict(r) for r in await cursor.fetchall()]
        interpretation = interpret_response(request.reply_text, strategy, [{"type": s['step_type'], "content": s['content'][:200]} for s in steps])
        await add_step(db, request.negotiation_id, "reply_received", {"reply": request.reply_text, "interpretation": interpretation}, interpretation.get('decision_reasoning', ''), interpretation.get('decision', ''))
        decision = interpretation.get('decision', 'close')
        offered = interpretation.get('offered_amount') or 0

        # Always track best offer and round count regardless of decision
        common_kwargs = {}
        current_best = neg.get('best_offer_received')
        if offered > 0:
            if current_best is None or offered < float(current_best):
                common_kwargs['best_offer_received'] = offered
        common_kwargs['rounds_count'] = (neg.get('rounds_count') or 0) + 1

        if decision == 'accept':
            current = float(neg.get('current_amount') or 0)
            if offered > 0 and current > 0:
                savings = max(0, current - offered)
            elif current > 0 and neg.get('target_price'):
                savings = max(0, current - float(neg['target_price']))
            else:
                savings = 0
            await update_status(db, request.negotiation_id, "won", savings_achieved=savings, **common_kwargs)
            await add_step(db, request.negotiation_id, "closed", {"outcome": "won", "final_amount": offered}, "Accepted offer", "DEAL CLOSED")
        elif decision == 'counter':
            async with db.execute("SELECT * FROM negotiations WHERE id = ?", (request.negotiation_id,)) as cursor:
                full_neg = await cursor.fetchone()
                if not full_neg: raise HTTPException(404, "Not found")
                full_neg = dict(full_neg)
            async with db.execute("SELECT * FROM bills WHERE id = ?", (full_neg["bill_id"],)) as cursor:
                bill = await cursor.fetchone()
                if not bill: raise HTTPException(404, "Bill not found")
                bill = dict(bill)
            bill_data = json.loads(bill.get('extracted_data') or '{}')
            research = json.loads(full_neg.get('research_findings') or '{}')
            counter = draft_negotiation_email(bill_data, research, strategy, round_num=len([s for s in steps if s['step_type'] == 'email_draft']) + 1, previous_response=request.reply_text)
            await add_step(db, request.negotiation_id, "email_draft", counter, "Counter-offer drafted", f"Counter: ${counter.get('ask_amount', 0):.2f}")
            await update_status(db, request.negotiation_id, "awaiting_reply", **common_kwargs)
        else:
            await update_status(db, request.negotiation_id, "closed_no_deal", **common_kwargs)
            await add_step(db, request.negotiation_id, "closed", {"outcome": "no_deal"}, "Ended without deal", "CLOSED")
    return {"interpretation": interpretation, "decision": decision}
