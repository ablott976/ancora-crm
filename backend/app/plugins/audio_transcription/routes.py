"""Audio transcription dashboard routes."""
from fastapi import APIRouter, Depends
from typing import Optional
from app.database import get_db
from app.routes.auth import get_current_user
from app.plugins.audio_transcription import services

router = APIRouter(prefix="/api/plugins/audio", tags=["audio_transcription"], dependencies=[Depends(get_current_user)])


@router.get("/transcriptions/{instance_id}")
async def list_transcriptions(instance_id: int, phone: Optional[str] = None, db=Depends(get_db)):
    return await services.list_transcriptions(db, instance_id, phone=phone)

@router.get("/stats/{instance_id}")
async def get_stats(instance_id: int, db=Depends(get_db)):
    return await services.get_stats(db, instance_id)
