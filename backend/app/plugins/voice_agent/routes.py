"""Voice agent dashboard routes."""
from fastapi import APIRouter, Depends
from typing import Optional
from pydantic import BaseModel
from app.database import get_db
from app.routes.auth import get_current_user
from app.plugins.voice_agent import services

router = APIRouter(prefix="/api/plugins/voice", tags=["voice_agent"], dependencies=[Depends(get_current_user)])


class VoiceConfig(BaseModel):
    instance_id: int
    provider: str = "twilio"
    phone_number: Optional[str] = None
    voice_model: Optional[str] = None
    greeting_text: Optional[str] = None
    max_call_duration_seconds: int = 300
    api_key: Optional[str] = None
    api_secret: Optional[str] = None


@router.get("/config/{instance_id}")
async def get_config(instance_id: int, db=Depends(get_db)):
    config = await services.get_config(db, instance_id)
    return config or {"configured": False}

@router.post("/config")
async def set_config(data: VoiceConfig, db=Depends(get_db)):
    return await services.upsert_config(db, data.instance_id, data.provider, data.phone_number, data.voice_model, data.greeting_text, data.max_call_duration_seconds, data.api_key, data.api_secret)

@router.get("/calls/{instance_id}")
async def list_calls(instance_id: int, db=Depends(get_db)):
    return await services.list_calls(db, instance_id)
