"""Restaurant bookings dashboard routes."""
from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
from datetime import date
from pydantic import BaseModel
from app.database import get_db
from app.routes.auth import get_current_user
from app.plugins.restaurant_bookings import services

router = APIRouter(prefix="/api/plugins/restaurant", tags=["restaurant_bookings"], dependencies=[Depends(get_current_user)])


class ZoneCreate(BaseModel):
    instance_id: int
    name: str
    capacity: int = 20


@router.get("/reservations/{instance_id}")
async def list_reservations(instance_id: int, date_filter: Optional[str] = None, db=Depends(get_db)):
    d = date.fromisoformat(date_filter) if date_filter else None
    return await services.list_reservations(db, instance_id, target_date=d)

@router.get("/zones/{instance_id}")
async def list_zones(instance_id: int, db=Depends(get_db)):
    return await services.list_zones(db, instance_id)

@router.post("/zones")
async def create_zone(data: ZoneCreate, db=Depends(get_db)):
    return await services.create_zone(db, data.instance_id, data.name, data.capacity)
