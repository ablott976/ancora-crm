"""Audio Transcription plugin - Transcripción automática de audios."""
from app.plugins.base import BasePlugin
from app.plugins.audio_transcription.routes import router as audio_router


class AudioTranscriptionPlugin(BasePlugin):
    id = "audio_transcription"
    name = "Transcripción de Audio"
    version = "1.0.0"
    dependencies = []
    description = "Transcripción automática de mensajes de voz con Gemini Flash"
    icon = "mic"

    def get_router(self):
        return audio_router

    def get_system_prompt_section(self, config: dict) -> str:
        return (
            "\n\n## AUDIO\n"
            "Los mensajes de voz del cliente se transcriben automáticamente. "
            "Recibirás el texto transcrito directamente. Responde de forma natural."
        )

    async def on_install(self, db, instance_id: int):
        await db.execute(SCHEMA_SQL)

    def get_frontend_routes(self):
        return [
            {"path": "transcriptions", "label": "Transcripciones", "icon": "mic"},
        ]


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS ancora_crm.plugin_audio_transcriptions (
    id SERIAL PRIMARY KEY,
    instance_id INTEGER NOT NULL REFERENCES ancora_crm.chatbot_instances(id) ON DELETE CASCADE,
    contact_phone VARCHAR(20),
    original_media_url TEXT,
    transcription_text TEXT,
    duration_seconds INTEGER,
    language VARCHAR(10) DEFAULT 'es',
    model_used VARCHAR(50) DEFAULT 'gemini-flash',
    tokens_used INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_audio_instance ON ancora_crm.plugin_audio_transcriptions(instance_id, created_at DESC);
"""
