"""Broadcasts dashboard routes."""
from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional
from pydantic import BaseModel, Field
from app.database import get_db
from app.plugins.base import require_plugin
from app.services.chatbot_auth import get_current_chatbot_user
from app.plugins.broadcasts import services

router = APIRouter()


class CampaignCreate(BaseModel):
    name: str
    message_template: str
    target_tags: list = Field(default_factory=list)
    scheduled_at: Optional[str] = None

class CampaignUpdate(BaseModel):
    name: Optional[str] = None
    message_template: Optional[str] = None
    target_tags: Optional[list] = None
    scheduled_at: Optional[str] = None
    status: Optional[str] = None

class RecipientCreate(BaseModel):
    phone: str
    name: Optional[str] = None
    tags: list = Field(default_factory=list)
    opt_in_marketing: bool = False


@router.get("/dashboard/{instance_id}/broadcasts/campaigns")
async def get_campaigns(
    instance_id: int = require_plugin("broadcasts"),
    status: Optional[str] = None,
    db=Depends(get_db),
    user=Depends(get_current_chatbot_user),
):
    return await services.list_campaigns(db, instance_id, status=status)

@router.post("/dashboard/{instance_id}/broadcasts/campaigns")
async def create_campaign(
    data: CampaignCreate,
    instance_id: int = require_plugin("broadcasts"),
    db=Depends(get_db),
    user=Depends(get_current_chatbot_user),
):
    return await services.create_campaign(db, instance_id, data.name, data.message_template, data.target_tags, data.scheduled_at)

@router.put("/dashboard/{instance_id}/broadcasts/campaigns/{campaign_id}")
async def update_campaign(
    campaign_id: int,
    data: CampaignUpdate,
    instance_id: int = require_plugin("broadcasts"),
    db=Depends(get_db),
    user=Depends(get_current_chatbot_user),
):
    result = await services.update_campaign(db, instance_id, campaign_id, **data.model_dump(exclude_unset=True))
    if not result:
        raise HTTPException(404, "Campaign not found")
    return result

@router.delete("/dashboard/{instance_id}/broadcasts/campaigns/{campaign_id}")
async def delete_campaign(
    campaign_id: int,
    instance_id: int = require_plugin("broadcasts"),
    db=Depends(get_db),
    user=Depends(get_current_chatbot_user),
):
    if not await services.delete_campaign(db, instance_id, campaign_id):
        raise HTTPException(400, "Only draft campaigns can be deleted")
    return {"message": "Campaign deleted"}

@router.post("/dashboard/{instance_id}/broadcasts/campaigns/{campaign_id}/send")
async def send_campaign(
    campaign_id: int,
    instance_id: int = require_plugin("broadcasts"),
    db=Depends(get_db),
    user=Depends(get_current_chatbot_user),
):
    try:
        return await services.send_campaign(db, instance_id, campaign_id)
    except ValueError as exc:
        message = str(exc)
        status_code = 404 if message == "Campaign not found" else 400
        raise HTTPException(status_code, message)

@router.get("/dashboard/{instance_id}/broadcasts/recipients")
async def get_recipients(
    instance_id: int = require_plugin("broadcasts"),
    opted_in_only: bool = False,
    db=Depends(get_db),
    user=Depends(get_current_chatbot_user),
):
    return await services.list_recipients(db, instance_id, opted_in_only=opted_in_only)

@router.post("/dashboard/{instance_id}/broadcasts/recipients")
async def add_recipient(
    data: RecipientCreate,
    instance_id: int = require_plugin("broadcasts"),
    db=Depends(get_db),
    user=Depends(get_current_chatbot_user),
):
    return await services.add_recipient(db, instance_id, data.phone, data.name, data.tags, data.opt_in_marketing)

@router.post("/dashboard/{instance_id}/broadcasts/recipients/{phone}/opt-out")
async def opt_out(
    phone: str,
    instance_id: int = require_plugin("broadcasts"),
    db=Depends(get_db),
    user=Depends(get_current_chatbot_user),
):
    if not await services.opt_out_recipient(db, instance_id, phone):
        raise HTTPException(404, "Recipient not found")
    return {"message": "Opted out"}

@router.get("/dashboard/{instance_id}/broadcasts/campaigns/{campaign_id}/send-log")
async def get_log(
    campaign_id: int,
    instance_id: int = require_plugin("broadcasts"),
    db=Depends(get_db),
    user=Depends(get_current_chatbot_user),
):
    return await services.get_send_log(db, instance_id, campaign_id)
