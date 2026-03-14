"""Owner agent dashboard routes."""
from fastapi import APIRouter, Depends
from typing import Optional
from pydantic import BaseModel
from app.database import get_db
from app.routes.auth import get_current_user
from app.plugins.owner_agent import services

router = APIRouter(prefix="/api/plugins/owner", tags=["owner_agent"], dependencies=[Depends(get_current_user)])


class OwnerConfig(BaseModel):
    instance_id: int
    owner_phone: str
    daily_summary_enabled: bool = True
    daily_summary_time: str = "21:00"


@router.get("/config/{instance_id}")
async def get_config(instance_id: int, db=Depends(get_db)):
    config = await services.get_config(db, instance_id)
    return config or {"configured": False}

@router.post("/config")
async def set_config(data: OwnerConfig, db=Depends(get_db)):
    return await services.set_config(db, data.instance_id, data.owner_phone, data.daily_summary_enabled, data.daily_summary_time)

@router.get("/summary/{instance_id}")
async def get_summary(instance_id: int, date: Optional[str] = None, db=Depends(get_db)):
    from datetime import date as d
    target = d.fromisoformat(date) if date else None
    return await services.get_daily_summary(db, instance_id, target)
