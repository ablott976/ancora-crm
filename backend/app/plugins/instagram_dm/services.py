"""Instagram DM business logic."""
from typing import List, Optional


async def get_config(db, instance_id: int) -> Optional[dict]:
    row = await db.fetchrow("SELECT * FROM ancora_crm.plugin_instagram_config WHERE instance_id = $1", instance_id)
    return dict(row) if row else None


async def upsert_config(db, instance_id: int, ig_page_id: str, ig_access_token: str, ig_username: str = None, webhook_verify_token: str = None) -> dict:
    row = await db.fetchrow(
        """INSERT INTO ancora_crm.plugin_instagram_config (instance_id, ig_page_id, ig_access_token, ig_username, webhook_verify_token, is_active)
           VALUES ($1, $2, $3, $4, $5, true)
           ON CONFLICT (instance_id) DO UPDATE SET ig_page_id = $2, ig_access_token = $3, ig_username = COALESCE($4, plugin_instagram_config.ig_username), webhook_verify_token = COALESCE($5, plugin_instagram_config.webhook_verify_token), updated_at = NOW()
           RETURNING *""",
        instance_id, ig_page_id, ig_access_token, ig_username, webhook_verify_token)
    return dict(row)


async def list_conversations(db, instance_id: int, include_resolved: bool = False, limit: int = 50) -> List[dict]:
    cond = "instance_id = $1"
    if not include_resolved:
        cond += " AND is_resolved = false"
    return [dict(r) for r in await db.fetch(f"SELECT * FROM ancora_crm.plugin_instagram_conversations WHERE {cond} ORDER BY last_message_at DESC NULLS LAST LIMIT {limit}", instance_id)]


async def get_or_create_conversation(db, instance_id: int, ig_user_id: str, ig_username: str = None, ig_name: str = None) -> dict:
    row = await db.fetchrow(
        """INSERT INTO ancora_crm.plugin_instagram_conversations (instance_id, ig_user_id, ig_username, ig_name, last_message_at)
           VALUES ($1, $2, $3, $4, NOW())
           ON CONFLICT (instance_id, ig_user_id) DO UPDATE SET ig_username = COALESCE($3, plugin_instagram_conversations.ig_username), ig_name = COALESCE($4, plugin_instagram_conversations.ig_name), last_message_at = NOW()
           RETURNING *""",
        instance_id, ig_user_id, ig_username, ig_name)
    return dict(row)


async def save_message(db, conversation_id: int, direction: str, message_text: str, ig_message_id: str = None, media_url: str = None) -> dict:
    row = await db.fetchrow(
        """INSERT INTO ancora_crm.plugin_instagram_messages (conversation_id, direction, message_text, ig_message_id, media_url)
           VALUES ($1, $2, $3, $4, $5) RETURNING *""",
        conversation_id, direction, message_text, ig_message_id, media_url)
    return dict(row)


async def get_messages(db, conversation_id: int, limit: int = 50) -> List[dict]:
    return [dict(r) for r in await db.fetch("SELECT * FROM ancora_crm.plugin_instagram_messages WHERE conversation_id = $1 ORDER BY created_at ASC LIMIT $2", conversation_id, limit)]


async def resolve_conversation(db, conversation_id: int) -> bool:
    result = await db.execute("UPDATE ancora_crm.plugin_instagram_conversations SET is_resolved = true WHERE id = $1", conversation_id)
    return int(result.split(" ")[1]) > 0
