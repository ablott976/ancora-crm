"""Instagram DM dashboard routes."""
from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
from pydantic import BaseModel
from app.database import get_db
from app.routes.auth import get_current_user
from app.plugins.instagram_dm import services

router = APIRouter(prefix="/api/plugins/instagram-dm", tags=["instagram_dm"], dependencies=[Depends(get_current_user)])


class IGConfigCreate(BaseModel):
    instance_id: int
    ig_page_id: str
    ig_access_token: str
    ig_username: Optional[str] = None
    webhook_verify_token: Optional[str] = None


@router.get("/config/{instance_id}")
async def get_config(instance_id: int, db=Depends(get_db)):
    config = await services.get_config(db, instance_id)
    if not config:
        return {"configured": False}
    safe = {k: v for k, v in config.items() if k != "ig_access_token"}
    safe["configured"] = True
    safe["token_set"] = bool(config.get("ig_access_token"))
    return safe

@router.post("/config")
async def set_config(data: IGConfigCreate, db=Depends(get_db)):
    return await services.upsert_config(db, data.instance_id, data.ig_page_id, data.ig_access_token, data.ig_username, data.webhook_verify_token)

@router.get("/conversations/{instance_id}")
async def get_conversations(instance_id: int, include_resolved: bool = False, db=Depends(get_db)):
    return await services.list_conversations(db, instance_id, include_resolved=include_resolved)

@router.get("/messages/{conversation_id}")
async def get_messages(conversation_id: int, db=Depends(get_db)):
    return await services.get_messages(db, conversation_id)

@router.post("/conversations/{conversation_id}/resolve")
async def resolve(conversation_id: int, db=Depends(get_db)):
    if not await services.resolve_conversation(db, conversation_id):
        raise HTTPException(404, "Conversation not found")
    return {"message": "Resolved"}
