"""Daily menus plugin - Menus diarios de restaurante."""
from app.plugins.base import BasePlugin
from app.plugins.daily_menus.routes import router as daily_menus_router
from app.plugins.daily_menus.tools import DAILY_MENU_TOOLS, DAILY_MENU_TOOL_HANDLERS


class DailyMenusPlugin(BasePlugin):
    id = "daily_menus"
    name = "Menus Diarios"
    version = "1.0.0"
    dependencies = []
    description = "Gestion de menus diarios del restaurante y sus platos"
    icon = "utensils"

    def get_router(self):
        return daily_menus_router

    def get_tools(self):
        return DAILY_MENU_TOOLS

    def get_tool_handlers(self):
        return DAILY_MENU_TOOL_HANDLERS

    def get_system_prompt_section(self, config: dict) -> str:
        return (
            "\n\n## MENUS DIARIOS\n"
            "Tienes acceso a los menus diarios del restaurante. Puedes:\n"
            "- Consultar el menu de hoy\n"
            "- Consultar el menu de una fecha concreta\n"
            "- Informar del nombre del menu, precio y platos incluidos\n"
            "- Indicar descripciones, tipo de plato y alergenos si estan disponibles\n"
            "Usa las herramientas disponibles para responder con informacion exacta del menu. "
            "Si no hay menu activo para la fecha solicitada, dilo claramente."
        )

    async def on_install(self, db, instance_id: int):
        """Create daily menu tables if they don't exist."""
        await db.execute(SCHEMA_SQL)

    def get_frontend_routes(self):
        return [
            {"path": "daily-menus", "label": "Menus Diarios", "icon": "utensils"},
        ]


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS ancora_crm.plugin_daily_menus (
    id SERIAL PRIMARY KEY,
    instance_id INTEGER NOT NULL REFERENCES ancora_crm.chatbot_instances(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    name VARCHAR(200) NOT NULL,
    price NUMERIC(10,2),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_daily_menus_instance_date
    ON ancora_crm.plugin_daily_menus(instance_id, date);

CREATE TABLE IF NOT EXISTS ancora_crm.plugin_daily_menu_items (
    id SERIAL PRIMARY KEY,
    menu_id INTEGER NOT NULL REFERENCES ancora_crm.plugin_daily_menus(id) ON DELETE CASCADE,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    course_type VARCHAR(100),
    allergens TEXT,
    sort_order INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_daily_menu_items_menu_sort
    ON ancora_crm.plugin_daily_menu_items(menu_id, sort_order, id);
"""
