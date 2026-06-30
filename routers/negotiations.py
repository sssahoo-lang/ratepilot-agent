from fastapi import APIRouter, HTTPException
import aiosqlite, json
from database import DB_PATH

router = APIRouter()

def _enrich_savings(row: dict) -> dict:
    neg = dict(row)
    savings = float(neg.get("savings_achieved") or 0)
    if savings <= 0 and neg.get("status") == "won":
        current = float(neg.get("current_amount") or 0)
        target = float(neg.get("target_price") or 0)
        if current > 0 and target > 0 and current > target:
            neg["savings_achieved"] = current - target
            savings = neg["savings_achieved"]
    # Compute monthly/annual once — frontend reads these as the single source of truth
    best = float(neg.get("best_offer_received") or 0)
    current = float(neg.get("current_amount") or 0)
    if best > 0 and current > 0 and current > best:
        monthly = current - best
    elif savings > 0:
        monthly = savings
    else:
        monthly = 0.0
    neg["monthly_savings"] = monthly
    neg["annual_savings"] = monthly * 12
    return neg

@router.get("/")
async def list_negotiations():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT n.*, b.provider, b.current_amount, b.bill_type, b.filename FROM negotiations n JOIN bills b ON n.bill_id = b.id ORDER BY n.created_at DESC") as cursor:
            return [_enrich_savings(r) for r in await cursor.fetchall()]

@router.get("/{negotiation_id}")
async def get_negotiation(negotiation_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT n.*, b.provider, b.current_amount, b.bill_type, b.filename, b.extracted_data FROM negotiations n JOIN bills b ON n.bill_id = b.id WHERE n.id = ?", (negotiation_id,)) as cursor:
            row = await cursor.fetchone()
            if not row: raise HTTPException(404, "Not found")
            neg = _enrich_savings(row)
        async with db.execute("SELECT * FROM negotiation_steps WHERE negotiation_id = ? ORDER BY created_at ASC", (negotiation_id,)) as cursor:
            steps = [dict(r) for r in await cursor.fetchall()]
        for step in steps:
            if step.get('content'):
                try: step['content'] = json.loads(step['content'])
                except: pass
        for field in ['research_findings', 'strategy', 'extracted_data']:
            if neg.get(field):
                try: neg[field] = json.loads(neg[field])
                except: pass
        neg['steps'] = steps
        return neg

@router.delete("/{negotiation_id}")
async def delete_negotiation(negotiation_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT id FROM negotiations WHERE id = ?", (negotiation_id,)) as cursor:
            if not await cursor.fetchone():
                raise HTTPException(404, "Not found")
        await db.execute("DELETE FROM negotiation_steps WHERE negotiation_id = ?", (negotiation_id,))
        await db.execute("DELETE FROM negotiations WHERE id = ?", (negotiation_id,))
        await db.commit()
    return {"message": "deleted", "id": negotiation_id}
