from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import aiosqlite
import json
from datetime import datetime
from database import DB_PATH
from gmail_service import send_email, check_for_reply

router = APIRouter()

class SendEmailRequest(BaseModel):
    negotiation_id: int
    to: str

class MarkSentRequest(BaseModel):
    negotiation_id: int
    to: str

class CheckReplyRequest(BaseModel):
    negotiation_id: int

@router.post("/send")
async def send_negotiation_email(request: SendEmailRequest):
    """Send the latest drafted email via Gmail."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        # Get latest email draft
        async with db.execute("""
            SELECT * FROM negotiation_steps 
            WHERE negotiation_id = ? AND step_type = 'email_draft'
            ORDER BY created_at DESC LIMIT 1
        """, (request.negotiation_id,)) as cursor:
            step = await cursor.fetchone()
            if not step:
                raise HTTPException(404, "No email draft found")
            
            content = json.loads(step['content'])
            subject = content.get('subject', 'Regarding my account')
            body = content.get('body', '')

        # Send via Gmail
        try:
            sent = send_email(request.to, subject, body)
        except Exception as e:
            raise HTTPException(500, f"Failed to send email: {str(e)}")

        message_id = sent['id']
        thread_id = sent['threadId']

        # Save thread info
        await db.execute("""
            UPDATE negotiations SET
            research_findings = json_set(COALESCE(research_findings, '{}'),
                '$.gmail_thread_to', ?,
                '$.gmail_message_id', ?,
                '$.gmail_thread_id', ?)
            WHERE id = ?
        """, (request.to, message_id, thread_id, request.negotiation_id))

        # Log the step
        await db.execute("""
            INSERT INTO negotiation_steps
            (negotiation_id, step_type, content, reasoning, decision)
            VALUES (?, 'email_sent', ?, ?, ?)
        """, (
            request.negotiation_id,
            json.dumps({"to": request.to, "subject": subject, "message_id": message_id, "thread_id": thread_id}),
            f"Email sent to {request.to}",
            f"Message ID: {message_id}"
        ))
        await db.commit()

    return {
        "message_id": message_id,
        "to": request.to,
        "subject": subject,
        "status": "sent"
    }

@router.post("/mark-sent")
async def mark_negotiation_email_sent(request: MarkSentRequest):
    """Record that the user manually sent the latest drafted email via Gmail."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        async with db.execute("""
            SELECT * FROM negotiation_steps
            WHERE negotiation_id = ? AND step_type = 'email_draft'
            ORDER BY created_at DESC LIMIT 1
        """, (request.negotiation_id,)) as cursor:
            step = await cursor.fetchone()
            if not step:
                raise HTTPException(404, "No email draft found")

            content = json.loads(step['content'])
            subject = content.get('subject', 'Regarding my account')

        await db.execute("""
            UPDATE negotiations SET
            research_findings = json_set(COALESCE(research_findings, '{}'), '$.gmail_thread_to', ?)
            WHERE id = ?
        """, (request.to, request.negotiation_id))

        await db.execute("""
            INSERT INTO negotiation_steps
            (negotiation_id, step_type, content, reasoning, decision)
            VALUES (?, 'email_sent', ?, ?, ?)
        """, (
            request.negotiation_id,
            json.dumps({"to": request.to, "subject": subject, "manual": True}),
            f"Email sent to {request.to} via Gmail",
            "Sent manually by user"
        ))
        await db.commit()

    return {"to": request.to, "subject": subject, "status": "sent"}


@router.post("/check-reply")
async def check_email_reply(request: CheckReplyRequest):
    """Check if the company has replied."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        async with db.execute("""
            SELECT content FROM negotiation_steps
            WHERE negotiation_id = ? AND step_type = 'email_sent'
            ORDER BY created_at DESC LIMIT 1
        """, (request.negotiation_id,)) as cursor:
            step = await cursor.fetchone()
            if not step:
                raise HTTPException(404, "No sent email found")

            content = json.loads(step['content'])
            message_id = content.get('message_id')
            thread_id = content.get('thread_id') or message_id

    if not thread_id:
        return {"has_reply": False, "manual": True}

    try:
        reply = check_for_reply(thread_id, [message_id])
        if reply:
            return {"has_reply": True, "reply": reply['body'], "reply_id": reply['id']}
        return {"has_reply": False}
    except Exception as e:
        raise HTTPException(500, f"Failed to check replies: {str(e)}")


@router.get("/provider-email/{provider_name}")
async def lookup_provider_email(provider_name: str):
    from provider_emails import get_provider_email
    return get_provider_email(provider_name)
