from fastapi import APIRouter, UploadFile, File, HTTPException
import aiosqlite
import asyncio
import json
import io
import re
from database import DB_PATH
from agent_service import MODEL, client, extract_json, parse_bill_from_image, call_with_retry
import pypdf

router = APIRouter()

SUPPORTED_IMAGE_TYPES = {
    "image/jpeg": "image/jpeg",
    "image/jpg": "image/jpeg",
    "image/png": "image/png",
    "image/gif": "image/gif",
    "image/webp": "image/webp",
}

def extract_text_from_pdf(file_bytes: bytes) -> str:
    reader = pypdf.PdfReader(io.BytesIO(file_bytes))
    return "".join(p.extract_text() + "\n" for p in reader.pages).strip()

def extract_bill_fields_cheap(text: str) -> dict:
    providers = ["AT&T", "Verizon", "Comcast", "Xfinity", "T-Mobile", "Spectrum", "Cox", "CenturyLink", "Dish", "DirecTV"]
    provider = next((p for p in providers if re.search(re.escape(p), text, re.IGNORECASE)), None)

    current_amount = None
    for pattern in [
        r"Total due\s*\$?([\d,]+\.?\d*)",
        r"Total amount due\s*\$?([\d,]+\.?\d*)",
        r"Amount due\s*\$?([\d,]+\.?\d*)",
        r"Balance due\s*\$?([\d,]+\.?\d*)",
    ]:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            current_amount = float(match.group(1).replace(",", ""))
            break

    account_number = None
    for pattern in [
        r"Account [Nn]umber[:\s]+([\d-]+)",
        r"Account #[:\s]*([\d-]+)",
        r"Acct[:\s]+([\d-]+)",
    ]:
        match = re.search(pattern, text)
        if match:
            account_number = match.group(1)
            break

    phone_numbers = set(re.findall(r"\b\d{3}[\.\-]\d{3}[\.\-]\d{4}\b", text))
    line_count = len(phone_numbers) or 1

    lowered = text.lower()
    if "wireless" in lowered or "mobile" in lowered:
        bill_type = "wireless"
    elif "internet" in lowered:
        bill_type = "internet"
    elif "cable" in lowered:
        bill_type = "cable"
    else:
        bill_type = "utility"

    account_tenure = None
    for pattern in [
        r"[Cc]ustomer since[:\s]+(\w+ \d{4})",
        r"[Mm]ember since[:\s]+(\w+ \d{4})",
    ]:
        match = re.search(pattern, text)
        if match:
            account_tenure = match.group(1)
            break

    return {
        "provider": provider,
        "current_amount": current_amount,
        "account_number": account_number,
        "line_count": line_count,
        "bill_type": bill_type,
        "account_tenure": account_tenure,
    }

def parse_bill_minimal(text: str) -> dict:
    response = call_with_retry(client.messages.create,
        model=MODEL,
        max_tokens=300,
        system="""You are a bill parsing expert. Extract only the most important fields.
Return ONLY JSON:
{
  "provider": "company name",
  "bill_type": "internet/wireless/cable/insurance/subscription/rent/utility/other",
  "current_amount": 99.99,
  "account_tenure": "2 years 3 months or null",
  "contract_end": "March 2025 or null",
  "account_number": "account number or null",
  "line_count": 1,
  "services": [],
  "payment_history": "good/unknown",
  "key_details": "short summary"
}
No preamble. JSON only.""",
        messages=[{"role": "user", "content": f"Parse this bill excerpt:\n\n{text[:800]}"}],
    )
    return extract_json(response.content[0].text)

def parse_text_bill_smart(raw_text: str, claude_text: str | None = None) -> dict:
    cheap = extract_bill_fields_cheap(raw_text)
    if cheap.get("provider") and cheap.get("current_amount") is not None:
        return {
            "provider": cheap.get("provider"),
            "bill_type": cheap.get("bill_type"),
            "current_amount": cheap.get("current_amount"),
            "account_tenure": cheap.get("account_tenure"),
            "contract_end": None,
            "account_number": cheap.get("account_number"),
            "line_count": cheap.get("line_count"),
            "services": [],
            "payment_history": "good",
            "key_details": f"Bill from {cheap.get('provider')} for ${cheap.get('current_amount')}",
        }
    return parse_bill_minimal((claude_text or raw_text)[:800])

@router.post("/upload")
async def upload_bill(file: UploadFile = File(...)):
    content = await file.read()
    content_type = file.content_type or ""
    filename = file.filename or ""
    extracted = None
    raw_text = ""

    # Image upload — use Claude vision
    if content_type in SUPPORTED_IMAGE_TYPES or filename.lower().endswith(('.jpg', '.jpeg', '.png', '.webp', '.gif')):
        media_type = SUPPORTED_IMAGE_TYPES.get(content_type, "image/jpeg")
        raw_text = "Image upload - text extracted via vision"
        try:
            extracted = await asyncio.to_thread(parse_bill_from_image, content, media_type)
        except Exception as e:
            raise HTTPException(400, f"Could not read image: {str(e)}")

    # PDF upload — extract text then parse
    elif filename.lower().endswith('.pdf') or content_type == "application/pdf":
        try:
            raw_text = extract_text_from_pdf(content)
            if not raw_text.strip():
                raise HTTPException(400, "Could not extract text from PDF")
            # Truncate to avoid token rate limits
            parse_text = raw_text[:3000]
            extracted = await asyncio.to_thread(parse_text_bill_smart, raw_text, parse_text)
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(400, f"Could not read PDF: {str(e)}")

    # Text upload
    elif filename.lower().endswith('.txt') or 'text' in content_type:
        raw_text = content.decode('utf-8')
        extracted = await asyncio.to_thread(parse_text_bill_smart, raw_text)

    else:
        raise HTTPException(400, "Supported formats: JPG, PNG, WEBP, PDF, TXT")

    if not extracted:
        raise HTTPException(500, "Could not parse bill data")

    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            INSERT INTO bills (filename, provider, current_amount, account_tenure,
                             contract_end, bill_type, raw_text, extracted_data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            filename,
            extracted.get('provider', 'Unknown'),
            float(extracted.get('current_amount', 0)),
            extracted.get('account_tenure', 'Unknown'),
            extracted.get('contract_end'),
            extracted.get('bill_type', 'other'),
            raw_text,
            json.dumps(extracted)
        ))
        bill_id = cursor.lastrowid
        await db.commit()

    return {
        "bill_id": bill_id,
        "extracted": extracted,
        "message": "Bill parsed successfully",
        "method": "vision" if content_type in SUPPORTED_IMAGE_TYPES else "text"
    }

@router.get("/")
async def list_bills():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM bills ORDER BY created_at DESC") as cursor:
            return [dict(r) for r in await cursor.fetchall()]

@router.get("/{bill_id}")
async def get_bill(bill_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM bills WHERE id = ?", (bill_id,)) as cursor:
            row = await cursor.fetchone()
            if not row:
                raise HTTPException(404, "Not found")
            data = dict(row)
            if data.get('extracted_data'):
                data['extracted_data'] = json.loads(data['extracted_data'])
            return data
