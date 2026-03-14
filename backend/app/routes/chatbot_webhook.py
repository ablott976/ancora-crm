from fastapi import APIRouter, Request, Response, Depends, HTTPException
import json
import logging
from app.services.chatbot_batcher import add_to_batch
from app.database import get_db

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/webhook/whatsapp")
async def whatsapp_webhook(request: Request, db=Depends(get_db)):
    """
    Handles incoming WhatsApp webhooks from n8n.
    Supports two payload formats:
    1) Full Meta webhook: { object, entry: [{ changes: [{ value, field }] }] }
    2) n8n pre-unwrapped: { messaging_product, metadata, contacts, messages, field }
    """
    try:
        payload = await request.json()
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    # Extract the 'value' dict containing messages, contacts, metadata
    values_to_process = []

    if "object" in payload and "entry" in payload:
        # Format 1: Full Meta webhook
        for entry in payload.get("entry", []):
            for change in entry.get("changes", []):
                if change.get("field") == "messages":
                    values_to_process.append(change.get("value", {}))
    elif "messaging_product" in payload:
        # Format 2: n8n sends the inner value directly
        if payload.get("field", "messages") == "messages":
            values_to_process.append(payload)
    else:
        logger.warning("Unrecognized webhook payload: %s", list(payload.keys()))
        return {"status": "ok"}

    for value in values_to_process:
        metadata = value.get("metadata", {})
        phone_number_id = metadata.get("phone_number_id")
        messages = value.get("messages")
        contacts = value.get("contacts")

        if not phone_number_id or not messages or not contacts:
            continue

        # Lookup chatbot instance by phone_number_id
        instance = await db.fetchrow(
            "SELECT id, is_active FROM ancora_crm.chatbot_instances WHERE phone_number_id = $1",
            phone_number_id
        )

        if not instance or not instance["is_active"]:
            logger.info("No active chatbot for phone_number_id=%s", phone_number_id)
            continue

        # Pass the full value to the batcher
        await add_to_batch(instance["id"], value)
        logger.info("Batched message for instance=%d (phone_number_id=%s)", instance["id"], phone_number_id)

    return {"status": "ok"}
