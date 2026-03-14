"""Broadcasts dashboard routes."""
from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional
from pydantic import BaseModel
from app.database import get_db
from app.routes.auth import get_current_user
from app.plugins.broadcasts import services

router = APIRouter(prefix="/api/plugins/broadcasts", tags=["broadcasts"], dependencies=[Depends(get_current_user)])


class CampaignCreate(BaseModel):
    instance_id: int
    name: str
    message_template: str
    target_tags: list = []
    scheduled_at: Optional[str] = None

class CampaignUpdate(BaseModel):
    name: Optional[str] = None
    message_template: Optional[str] = None
    target_tags: Optional[list] = None
    scheduled_at: Optional[str] = None
    status: Optional[str] = None

class RecipientCreate(BaseModel):
    instance_id: int
    phone: str
    name: Optional[str] = None
    tags: list = []
    opt_in_marketing: bool = False


@router.get("/campaigns/{instance_id}")
async def get_campaigns(instance_id: int, status: Optional[str] = None, db=Depends(get_db)):
    return await services.list_campaigns(db, instance_id, status=status)

@router.post("/campaigns")
async def create_campaign(data: CampaignCreate, db=Depends(get_db)):
    return await services.create_campaign(db, data.instance_id, data.name, data.message_template, data.target_tags, data.scheduled_at)

@router.put("/campaigns/{instance_id}/{campaign_id}")
async def update_campaign(instance_id: int, campaign_id: int, data: CampaignUpdate, db=Depends(get_db)):
    result = await services.update_campaign(db, instance_id, campaign_id, **data.model_dump(exclude_unset=True))
    if not result:
        raise HTTPException(404, "Campaign not found")
    return result

@router.delete("/campaigns/{instance_id}/{campaign_id}")
async def delete_campaign(instance_id: int, campaign_id: int, db=Depends(get_db)):
    if not await services.delete_campaign(db, instance_id, campaign_id):
        raise HTTPException(400, "Only draft campaigns can be deleted")
    return {"message": "Campaign deleted"}

@router.get("/recipients/{instance_id}")
async def get_recipients(instance_id: int, opted_in_only: bool = False, db=Depends(get_db)):
    return await services.list_recipients(db, instance_id, opted_in_only=opted_in_only)

@router.post("/recipients")
async def add_recipient(data: RecipientCreate, db=Depends(get_db)):
    return await services.add_recipient(db, data.instance_id, data.phone, data.name, data.tags, data.opt_in_marketing)

@router.post("/recipients/{instance_id}/{phone}/opt-out")
async def opt_out(instance_id: int, phone: str, db=Depends(get_db)):
    if not await services.opt_out_recipient(db, instance_id, phone):
        raise HTTPException(404, "Recipient not found")
    return {"message": "Opted out"}

@router.get("/send-log/{campaign_id}")
async def get_log(campaign_id: int, db=Depends(get_db)):
    return await services.get_send_log(db, campaign_id)
