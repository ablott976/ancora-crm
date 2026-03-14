"""Instagram DM plugin - Automatización de mensajes directos de Instagram."""
from app.plugins.base import BasePlugin
from app.plugins.instagram_dm.routes import router as ig_router


class InstagramDMPlugin(BasePlugin):
    id = "instagram_dm"
    name = "Instagram DM"
    version = "1.0.0"
    dependencies = []
    description = "Gestión de mensajes directos de Instagram via Graph API"
    icon = "instagram"

    def get_router(self):
        return ig_router

    async def on_install(self, db, instance_id: int):
        await db.execute(SCHEMA_SQL)

    def get_frontend_routes(self):
        return [
            {"path": "instagram-config", "label": "Instagram Config", "icon": "settings"},
            {"path": "instagram-conversations", "label": "Instagram DMs", "icon": "message-circle"},
        ]


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS ancora_crm.plugin_instagram_config (
    id SERIAL PRIMARY KEY,
    instance_id INTEGER NOT NULL REFERENCES ancora_crm.chatbot_instances(id) ON DELETE CASCADE,
    ig_page_id VARCHAR(100),
    ig_access_token TEXT,
    ig_username VARCHAR(100),
    is_active BOOLEAN DEFAULT false,
    webhook_verify_token VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(instance_id)
);

CREATE TABLE IF NOT EXISTS ancora_crm.plugin_instagram_conversations (
    id SERIAL PRIMARY KEY,
    instance_id INTEGER NOT NULL REFERENCES ancora_crm.chatbot_instances(id) ON DELETE CASCADE,
    ig_user_id VARCHAR(100) NOT NULL,
    ig_username VARCHAR(100),
    ig_name VARCHAR(200),
    last_message_at TIMESTAMPTZ,
    is_resolved BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(instance_id, ig_user_id)
);

CREATE TABLE IF NOT EXISTS ancora_crm.plugin_instagram_messages (
    id SERIAL PRIMARY KEY,
    conversation_id INTEGER NOT NULL REFERENCES ancora_crm.plugin_instagram_conversations(id) ON DELETE CASCADE,
    direction VARCHAR(3) NOT NULL CHECK (direction IN ('in', 'out')),
    message_text TEXT,
    ig_message_id VARCHAR(100),
    media_url TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_ig_conversations_instance ON ancora_crm.plugin_instagram_conversations(instance_id, last_message_at DESC);
CREATE INDEX IF NOT EXISTS idx_ig_messages_conv ON ancora_crm.plugin_instagram_messages(conversation_id, created_at);
"""
