"""Broadcasts plugin - Campañas WhatsApp marketing."""
from app.plugins.base import BasePlugin
from app.plugins.broadcasts.routes import router as broadcasts_router


class BroadcastsPlugin(BasePlugin):
    id = "broadcasts"
    name = "Campañas WhatsApp"
    version = "1.0.0"
    dependencies = []
    description = "Campañas de marketing por WhatsApp con opt-in GDPR"
    icon = "megaphone"

    def get_router(self):
        return broadcasts_router

    async def on_install(self, db, instance_id: int):
        await db.execute(SCHEMA_SQL)

    def get_frontend_routes(self):
        return [
            {"path": "campaigns", "label": "Campañas", "icon": "megaphone"},
            {"path": "recipients", "label": "Destinatarios", "icon": "users"},
        ]


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS ancora_crm.plugin_broadcasts_recipients (
    id SERIAL PRIMARY KEY,
    instance_id INTEGER NOT NULL REFERENCES ancora_crm.chatbot_instances(id) ON DELETE CASCADE,
    phone VARCHAR(20) NOT NULL,
    name VARCHAR(200),
    tags TEXT[] DEFAULT '{}',
    opt_in_marketing BOOLEAN DEFAULT false,
    opt_in_at TIMESTAMPTZ,
    opted_out_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(instance_id, phone)
);

CREATE TABLE IF NOT EXISTS ancora_crm.plugin_broadcasts_campaigns (
    id SERIAL PRIMARY KEY,
    instance_id INTEGER NOT NULL REFERENCES ancora_crm.chatbot_instances(id) ON DELETE CASCADE,
    name VARCHAR(200) NOT NULL,
    message_template TEXT NOT NULL,
    target_tags TEXT[] DEFAULT '{}',
    scheduled_at TIMESTAMPTZ,
    status VARCHAR(20) DEFAULT 'draft',
    total_recipients INTEGER DEFAULT 0,
    total_sent INTEGER DEFAULT 0,
    total_delivered INTEGER DEFAULT 0,
    total_failed INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ancora_crm.plugin_broadcasts_send_log (
    id SERIAL PRIMARY KEY,
    campaign_id INTEGER NOT NULL REFERENCES ancora_crm.plugin_broadcasts_campaigns(id) ON DELETE CASCADE,
    recipient_phone VARCHAR(20) NOT NULL,
    recipient_name VARCHAR(200),
    status VARCHAR(20) DEFAULT 'pending',
    sent_at TIMESTAMPTZ,
    delivered_at TIMESTAMPTZ,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_broadcasts_log_campaign ON ancora_crm.plugin_broadcasts_send_log(campaign_id, status);
CREATE INDEX IF NOT EXISTS idx_broadcasts_recipients_instance ON ancora_crm.plugin_broadcasts_recipients(instance_id, opt_in_marketing);
"""
