"""Consent forms dashboard routes."""
from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
from pydantic import BaseModel
from app.database import get_db
from app.routes.auth import get_current_user
from app.plugins.consent_forms import services

router = APIRouter(prefix="/api/plugins/consents", tags=["consent_forms"], dependencies=[Depends(get_current_user)])


class TemplateCreate(BaseModel):
    instance_id: int
    name: str
    content_html: str
    service_id: Optional[int] = None
    requires_id_number: bool = False
    requires_signature: bool = True

class ConsentCreate(BaseModel):
    instance_id: int
    template_id: int
    client_name: str
    client_phone: Optional[str] = None
    appointment_id: Optional[int] = None

class SignConsent(BaseModel):
    signature_data: Optional[str] = None
    id_number: Optional[str] = None


@router.get("/templates/{instance_id}")
async def list_templates(instance_id: int, db=Depends(get_db)):
    return await services.list_templates(db, instance_id)

@router.post("/templates")
async def create_template(data: TemplateCreate, db=Depends(get_db)):
    return await services.create_template(db, data.instance_id, data.name, data.content_html, data.service_id, data.requires_id_number, data.requires_signature)

@router.get("/records/{instance_id}")
async def list_records(instance_id: int, status: Optional[str] = None, db=Depends(get_db)):
    return await services.list_records(db, instance_id, status=status)

@router.post("/records")
async def create_record(data: ConsentCreate, db=Depends(get_db)):
    return await services.create_consent_record(db, data.instance_id, data.template_id, data.client_name, data.client_phone, data.appointment_id)

@router.post("/records/{record_id}/sign")
async def sign(record_id: int, data: SignConsent, db=Depends(get_db)):
    result = await services.sign_consent(db, record_id, data.signature_data, data.id_number)
    if not result:
        raise HTTPException(404, "Record not found")
    return result
