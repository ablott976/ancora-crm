"""Advanced CRM dashboard routes."""
from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
from pydantic import BaseModel
from app.database import get_db
from app.routes.auth import get_current_user
from app.plugins.advanced_crm import services

router = APIRouter(prefix="/api/plugins/crm", tags=["advanced_crm"], dependencies=[Depends(get_current_user)])


class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    tags: Optional[list] = None
    notes: Optional[str] = None
    vip_status: Optional[bool] = None

class InteractionCreate(BaseModel):
    interaction_type: str
    description: Optional[str] = None
    amount: Optional[float] = None


@router.get("/profiles/{instance_id}")
async def list_profiles(instance_id: int, vip_only: bool = False, search: Optional[str] = None, db=Depends(get_db)):
    return await services.list_profiles(db, instance_id, vip_only=vip_only, search=search)

@router.get("/profiles/{instance_id}/{profile_id}")
async def get_profile(instance_id: int, profile_id: int, db=Depends(get_db)):
    profiles = await services.list_profiles(db, instance_id)
    profile = next((p for p in profiles if p["id"] == profile_id), None)
    if not profile:
        raise HTTPException(404, "Profile not found")
    return profile

@router.put("/profiles/{instance_id}/{profile_id}")
async def update_profile(instance_id: int, profile_id: int, data: ProfileUpdate, db=Depends(get_db)):
    result = await services.update_profile(db, instance_id, profile_id, **data.model_dump(exclude_unset=True))
    if not result:
        raise HTTPException(404, "Profile not found")
    return result

@router.get("/history/{profile_id}")
async def get_history(profile_id: int, db=Depends(get_db)):
    return await services.get_customer_history(db, profile_id)

@router.post("/interactions/{profile_id}")
async def add_interaction(profile_id: int, data: InteractionCreate, db=Depends(get_db)):
    return await services.add_interaction(db, profile_id, data.interaction_type, data.description, data.amount)
