"""Reminders plugin API routes."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.database import get_db
from app.plugins.base import require_plugin
from app.services.chatbot_auth import get_current_chatbot_user
from app.plugins.reminders import services as svc

router = APIRouter()


class TemplateCreate(BaseModel):
    name: str
    type: str = "pre"  # pre or post
    hours_before: int = 24
    template_text: str
    send_to: str = "client"  # client or professional


class TemplateUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    hours_before: Optional[int] = None
    template_text: Optional[str] = None
    is_active: Optional[bool] = None
    send_to: Optional[str] = None


@router.get("/dashboard/{instance_id}/reminders/templates")
async def list_templates(
    instance_id: int = require_plugin("reminders"),
    db=Depends(get_db),
    user=Depends(get_current_chatbot_user),
):
    return await svc.list_templates(db, instance_id)


@router.post("/dashboard/{instance_id}/reminders/templates", status_code=201)
async def create_template(
    data: TemplateCreate,
    instance_id: int = require_plugin("reminders"),
    db=Depends(get_db),
    user=Depends(get_current_chatbot_user),
):
    return await svc.create_template(
        db, instance_id, data.name, data.type, data.hours_before,
        data.template_text, data.send_to,
    )


@router.put("/dashboard/{instance_id}/reminders/templates/{template_id}")
async def update_template(
    template_id: int,
    data: TemplateUpdate,
    instance_id: int = require_plugin("reminders"),
    db=Depends(get_db),
    user=Depends(get_current_chatbot_user),
):
    result = await svc.update_template(db, instance_id, template_id, **data.dict(exclude_unset=True))
    if not result:
        raise HTTPException(status_code=404, detail="Plantilla no encontrada")
    return result


@router.delete("/dashboard/{instance_id}/reminders/templates/{template_id}", status_code=204)
async def delete_template(
    template_id: int,
    instance_id: int = require_plugin("reminders"),
    db=Depends(get_db),
    user=Depends(get_current_chatbot_user),
):
    if not await svc.delete_template(db, instance_id, template_id):
        raise HTTPException(status_code=404, detail="Plantilla no encontrada")


@router.get("/dashboard/{instance_id}/reminders/log")
async def get_log(
    instance_id: int = require_plugin("reminders"),
    limit: int = 50,
    db=Depends(get_db),
    user=Depends(get_current_chatbot_user),
):
    return await svc.get_reminder_log(db, instance_id, limit)


@router.post("/dashboard/{instance_id}/reminders/check")
async def trigger_check(
    instance_id: int = require_plugin("reminders"),
    db=Depends(get_db),
    user=Depends(get_current_chatbot_user),
):
    """Manually trigger a reminder check (for testing)."""
    count = await svc.check_and_send_reminders(db, instance_id)
    return {"checked": True, "reminders_created": count}
