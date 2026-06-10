from fastapi import APIRouter, UploadFile, File, HTTPException, Response
import aiosqlite
import json
import io
from database import DB_PATH
from agent_service import parse_bill, parse_bill_from_image
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
            extracted = parse_bill_from_image(content, media_type)
        except Exception as e:
            raise HTTPException(400, f"Could not read image: {str(e)}")

    # PDF upload — extract text then parse
    elif filename.lower().endswith('.pdf') or content_type == "application/pdf":
        try:
            raw_text = extract_text_from_pdf(content)
            if not raw_text.strip():
                raise HTTPException(400, "Could not extract text from PDF")
            extracted = parse_bill(raw_text)
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(400, f"Could not read PDF: {str(e)}")

    # Text upload
    elif filename.lower().endswith('.txt') or 'text' in content_type:
        raw_text = content.decode('utf-8')
        extracted = parse_bill(raw_text)

    else:
        raise HTTPException(400, "Supported formats: JPG, PNG, WEBP, PDF, TXT")

    if not extracted:
        raise HTTPException(500, "Could not parse bill data")

    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            INSERT INTO bills (filename, provider, current_amount, account_tenure,
                             contract_end, bill_type, raw_text, extracted_data,
                             file_data, file_mimetype)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            filename,
            extracted.get('provider', 'Unknown'),
            float(extracted.get('current_amount', 0)),
            extracted.get('account_tenure', 'Unknown'),
            extracted.get('contract_end'),
            extracted.get('bill_type', 'other'),
            raw_text,
            json.dumps(extracted),
            content,
            content_type
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

@router.get("/{bill_id}/file")
async def get_bill_file(bill_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT file_data, file_mimetype FROM bills WHERE id = ?", (bill_id,)) as cursor:
            row = await cursor.fetchone()
            if not row or row["file_data"] is None:
                raise HTTPException(404, "No file stored")
            return Response(
                content=row["file_data"],
                media_type=row["file_mimetype"],
                headers={"Content-Disposition": "inline"}
            )

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
