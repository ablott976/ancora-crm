"""Owner agent business logic."""
from typing import Optional
from datetime import date


async def get_config(db, instance_id: int) -> Optional[dict]:
    row = await db.fetchrow("SELECT * FROM ancora_crm.plugin_owner_config WHERE instance_id = $1", instance_id)
    return dict(row) if row else None


async def set_config(db, instance_id: int, owner_phone: str, daily_summary: bool = True, summary_time: str = "21:00") -> dict:
    row = await db.fetchrow(
        """INSERT INTO ancora_crm.plugin_owner_config (instance_id, owner_phone, daily_summary_enabled, daily_summary_time)
           VALUES ($1, $2, $3, $4)
           ON CONFLICT (instance_id) DO UPDATE SET owner_phone = $2, daily_summary_enabled = $3, daily_summary_time = $4
           RETURNING *""",
        instance_id, owner_phone, daily_summary, summary_time)
    return dict(row)


async def is_owner(db, instance_id: int, phone: str) -> bool:
    row = await db.fetchrow("SELECT 1 FROM ancora_crm.plugin_owner_config WHERE instance_id = $1 AND owner_phone = $2 AND is_active = true", instance_id, phone)
    return row is not None


async def get_daily_summary(db, instance_id: int, target_date: date = None) -> dict:
    d = target_date or date.today()
    conversations = await db.fetchval("SELECT COUNT(*) FROM ancora_crm.chatbot_conversations WHERE instance_id = $1 AND created_at::date = $2", instance_id, d)
    messages = await db.fetchval("SELECT COUNT(*) FROM ancora_crm.chatbot_messages WHERE instance_id = $1 AND created_at::date = $2", instance_id, d)
    # Try bookings if available
    bookings = 0
    try:
        bookings = await db.fetchval("SELECT COUNT(*) FROM ancora_crm.plugin_bookings_appointments WHERE instance_id = $1 AND created_at::date = $2", instance_id, d) or 0
    except Exception:
        pass
    return {"date": d.isoformat(), "conversations": conversations or 0, "messages": messages or 0, "new_bookings": bookings}


async def log_query(db, instance_id: int, query: str, response: str) -> dict:
    row = await db.fetchrow("INSERT INTO ancora_crm.plugin_owner_queries (instance_id, query_text, response_text) VALUES ($1, $2, $3) RETURNING *", instance_id, query, response)
    return dict(row)
