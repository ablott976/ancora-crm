"""Voice agent business logic."""
from typing import List, Optional


async def get_config(db, instance_id: int) -> Optional[dict]:
    row = await db.fetchrow("SELECT * FROM ancora_crm.plugin_voice_config WHERE instance_id = $1", instance_id)
    if not row:
        return None
    safe = dict(row)
    safe.pop("api_key", None)
    safe.pop("api_secret", None)
    safe["credentials_set"] = bool(row.get("api_key"))
    return safe


async def upsert_config(db, instance_id: int, provider: str = "twilio", phone_number: str = None, voice_model: str = None, greeting: str = None, max_duration: int = 300, api_key: str = None, api_secret: str = None) -> dict:
    row = await db.fetchrow(
        """INSERT INTO ancora_crm.plugin_voice_config (instance_id, provider, phone_number, voice_model, greeting_text, max_call_duration_seconds, api_key, api_secret, is_active)
           VALUES ($1, $2, $3, $4, $5, $6, $7, $8, true)
           ON CONFLICT (instance_id) DO UPDATE SET provider = COALESCE($2, plugin_voice_config.provider), phone_number = COALESCE($3, plugin_voice_config.phone_number), voice_model = COALESCE($4, plugin_voice_config.voice_model), greeting_text = COALESCE($5, plugin_voice_config.greeting_text), max_call_duration_seconds = $6, api_key = COALESCE($7, plugin_voice_config.api_key), api_secret = COALESCE($8, plugin_voice_config.api_secret), updated_at = NOW()
           RETURNING *""",
        instance_id, provider, phone_number, voice_model, greeting, max_duration, api_key, api_secret)
    return dict(row)


async def log_call(db, instance_id: int, caller_phone: str, call_sid: str = None, direction: str = "inbound") -> dict:
    row = await db.fetchrow(
        "INSERT INTO ancora_crm.plugin_voice_calls (instance_id, caller_phone, call_sid, direction) VALUES ($1, $2, $3, $4) RETURNING *",
        instance_id, caller_phone, call_sid, direction)
    return dict(row)


async def end_call(db, call_id: int, duration: int, transcript: str = None, summary: str = None, actions: list = None) -> Optional[dict]:
    row = await db.fetchrow(
        "UPDATE ancora_crm.plugin_voice_calls SET status = 'completed', duration_seconds = $2, transcript = $3, summary = $4, actions_taken = $5, ended_at = NOW() WHERE id = $1 RETURNING *",
        call_id, duration, transcript, summary, actions or [])
    return dict(row) if row else None


async def list_calls(db, instance_id: int, limit: int = 50) -> List[dict]:
    return [dict(r) for r in await db.fetch("SELECT * FROM ancora_crm.plugin_voice_calls WHERE instance_id = $1 ORDER BY started_at DESC LIMIT $2", instance_id, limit)]
