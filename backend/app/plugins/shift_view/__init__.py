"""Shift View plugin - Vista de turnos y agenda."""
from app.plugins.base import BasePlugin
from app.plugins.shift_view.routes import router as shift_router
from app.plugins.shift_view.tools import SHIFT_TOOLS, SHIFT_TOOL_HANDLERS


class ShiftViewPlugin(BasePlugin):
    id = "shift_view"
    name = "Vista de Turnos"
    version = "1.0.0"
    dependencies = ["bookings"]
    description = "Vista de agenda por profesional/día con gestión de turnos"
    icon = "calendar"

    def get_router(self):
        return shift_router

    def get_tools(self):
        return SHIFT_TOOLS

    def get_tool_handlers(self):
        return SHIFT_TOOL_HANDLERS

    def get_system_prompt_section(self, config: dict) -> str:
        return (
            "\n\n## TURNOS\n"
            "Puedes consultar la agenda de un profesional para un día concreto, "
            "mostrando sus citas y huecos libres."
        )

    async def on_install(self, db, instance_id: int):
        await db.execute(SCHEMA_SQL)

    def get_frontend_routes(self):
        return [
            {"path": "shifts", "label": "Turnos", "icon": "calendar"},
        ]


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS ancora_crm.plugin_shifts (
    id SERIAL PRIMARY KEY,
    instance_id INTEGER NOT NULL REFERENCES ancora_crm.chatbot_instances(id) ON DELETE CASCADE,
    professional_id INTEGER NOT NULL REFERENCES ancora_crm.plugin_bookings_professionals(id) ON DELETE CASCADE,
    day_of_week INTEGER NOT NULL CHECK (day_of_week BETWEEN 0 AND 6),
    start_time VARCHAR(5) NOT NULL,
    end_time VARCHAR(5) NOT NULL,
    is_active BOOLEAN DEFAULT true,
    UNIQUE(instance_id, professional_id, day_of_week, start_time)
);

CREATE TABLE IF NOT EXISTS ancora_crm.plugin_shift_overrides (
    id SERIAL PRIMARY KEY,
    instance_id INTEGER NOT NULL REFERENCES ancora_crm.chatbot_instances(id) ON DELETE CASCADE,
    professional_id INTEGER NOT NULL REFERENCES ancora_crm.plugin_bookings_professionals(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    start_time VARCHAR(5),
    end_time VARCHAR(5),
    is_off BOOLEAN DEFAULT false,
    reason VARCHAR(200),
    UNIQUE(instance_id, professional_id, date)
);
"""
