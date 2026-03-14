"""Audio transcription business logic."""
from typing import List, Optional


async def save_transcription(db, instance_id: int, contact_phone: str, media_url: str, text: str, duration: int = None, language: str = "es", model: str = "gemini-flash", tokens: int = None) -> dict:
    row = await db.fetchrow(
        """INSERT INTO ancora_crm.plugin_audio_transcriptions (instance_id, contact_phone, original_media_url, transcription_text, duration_seconds, language, model_used, tokens_used)
           VALUES ($1, $2, $3, $4, $5, $6, $7, $8) RETURNING *""",
        instance_id, contact_phone, media_url, text, duration, language, model, tokens)
    return dict(row)


async def list_transcriptions(db, instance_id: int, phone: str = None, limit: int = 50) -> List[dict]:
    if phone:
        return [dict(r) for r in await db.fetch("SELECT * FROM ancora_crm.plugin_audio_transcriptions WHERE instance_id = $1 AND contact_phone = $2 ORDER BY created_at DESC LIMIT $3", instance_id, phone, limit)]
    return [dict(r) for r in await db.fetch("SELECT * FROM ancora_crm.plugin_audio_transcriptions WHERE instance_id = $1 ORDER BY created_at DESC LIMIT $2", instance_id, limit)]


async def get_stats(db, instance_id: int) -> dict:
    row = await db.fetchrow("SELECT COUNT(*) as total, SUM(duration_seconds) as total_duration, SUM(tokens_used) as total_tokens FROM ancora_crm.plugin_audio_transcriptions WHERE instance_id = $1", instance_id)
    return dict(row) if row else {"total": 0, "total_duration": 0, "total_tokens": 0}
