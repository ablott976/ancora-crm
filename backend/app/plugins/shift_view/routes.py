"""Shift view dashboard routes."""
from fastapi import APIRouter, Depends
from typing import Optional
from datetime import date
from pydantic import BaseModel
from app.database import get_db
from app.routes.auth import get_current_user
from app.plugins.shift_view import services

router = APIRouter(prefix="/api/plugins/shifts", tags=["shift_view"], dependencies=[Depends(get_current_user)])


class ShiftCreate(BaseModel):
    instance_id: int
    professional_id: int
    day_of_week: int
    start_time: str
    end_time: str

class OverrideCreate(BaseModel):
    instance_id: int
    professional_id: int
    date: str
    is_off: bool = False
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    reason: Optional[str] = None


@router.get("/{instance_id}")
async def get_shifts(instance_id: int, professional_id: Optional[int] = None, db=Depends(get_db)):
    return await services.get_shifts(db, instance_id, professional_id)

@router.post("/")
async def create_shift(data: ShiftCreate, db=Depends(get_db)):
    return await services.set_shift(db, data.instance_id, data.professional_id, data.day_of_week, data.start_time, data.end_time)

@router.get("/agenda/{instance_id}/{professional_id}")
async def get_agenda(instance_id: int, professional_id: int, date_str: str, db=Depends(get_db)):
    return await services.get_day_agenda(db, instance_id, professional_id, date.fromisoformat(date_str))

@router.post("/overrides")
async def create_override(data: OverrideCreate, db=Depends(get_db)):
    return await services.set_override(db, data.instance_id, data.professional_id, date.fromisoformat(data.date), data.is_off, data.start_time, data.end_time, data.reason)
