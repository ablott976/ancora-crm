import os
import shutil
import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from app.database import get_db
from app.models.domain import Invoice, InvoiceUpdate
from app.services.invoice_analyzer import analyze_invoice_pdf
from app.config import settings
from app.routes.auth import get_current_user

router = APIRouter(dependencies=[Depends(get_current_user)])

@router.get("", response_model=List[dict])
async def get_invoices(client_id: Optional[int] = None, db = Depends(get_db)):
    if client_id:
        rows = await db.fetch("SELECT * FROM ancora_crm.invoices WHERE client_id = $1 ORDER BY created_at DESC", client_id)
    else:
        rows = await db.fetch("SELECT * FROM ancora_crm.invoices ORDER BY created_at DESC")
    return [dict(row) for row in rows]

@router.post("/upload")
async def upload_invoice(
    client_id: int = Form(...),
    file: UploadFile = File(...),
    db = Depends(get_db)
):
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    os.makedirs(settings.upload_dir, exist_ok=True)
    file_path = os.path.join(settings.upload_dir, file.filename)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    # Analyze with AI
    analysis_result = await analyze_invoice_pdf(file_path)
    
    extracted_data = {}
    ai_confidence = None
    if analysis_result.get("success"):
        extracted_data = analysis_result.get("data", {})
        ai_confidence = analysis_result.get("confidence")
    
    # Insert to DB
    query = """
    INSERT INTO ancora_crm.invoices (client_id, file_path, file_name, status, ai_extracted_data, ai_confidence)
    VALUES ($1, $2, $3, 'pending', $4, $5)
    RETURNING *
    """
    try:
        row = await db.fetchrow(query, client_id, file_path, file.filename, json.dumps(extracted_data), ai_confidence)
        return dict(row)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/{invoice_id}", response_model=Invoice)
async def update_invoice(invoice_id: int, invoice: InvoiceUpdate, db = Depends(get_db)):
    update_data = invoice.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    set_clauses = []
    values = []
    for i, (key, value) in enumerate(update_data.items(), start=1):
        set_clauses.append(f"{key} = ${i}")
        values.append(value)
    
    values.append(invoice_id)
    query = f"""
    UPDATE ancora_crm.invoices
    SET {', '.join(set_clauses)}, updated_at = NOW()
    WHERE id = ${len(values)}
    RETURNING *
    """
    row = await db.fetchrow(query, *values)
    if not row:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return dict(row)

@router.delete("/{invoice_id}")
async def delete_invoice(invoice_id: int, db = Depends(get_db)):
    row = await db.fetchrow("DELETE FROM ancora_crm.invoices WHERE id = $1 RETURNING id", invoice_id)
    if not row:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return {"message": "Invoice deleted"}

@router.get("/{invoice_id}/download")
async def download_invoice(invoice_id: int, db = Depends(get_db)):
    row = await db.fetchrow("SELECT file_path, file_name FROM ancora_crm.invoices WHERE id = $1", invoice_id)
    if not row or not row['file_path'] or not os.path.exists(row['file_path']):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path=row['file_path'], filename=row['file_name'])

@router.post("/{invoice_id}/analyze")
async def analyze_invoice(invoice_id: int, db = Depends(get_db)):
    row = await db.fetchrow("SELECT file_path FROM ancora_crm.invoices WHERE id = $1", invoice_id)
    if not row or not row['file_path'] or not os.path.exists(row['file_path']):
        raise HTTPException(status_code=404, detail="File not found")
    
    analysis_result = await analyze_invoice_pdf(row['file_path'])
    if not analysis_result.get("success"):
        raise HTTPException(status_code=500, detail=analysis_result.get("error"))
    
    extracted_data = analysis_result.get("data", {})
    ai_confidence = analysis_result.get("confidence")
    
    update_row = await db.fetchrow(
        "UPDATE ancora_crm.invoices SET ai_extracted_data = $1, ai_confidence = $2, updated_at = NOW() WHERE id = $3 RETURNING *",
        json.dumps(extracted_data), ai_confidence, invoice_id
    )
    return dict(update_row)
