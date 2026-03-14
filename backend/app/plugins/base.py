"""Base plugin infrastructure for Ancora CRM."""
from __future__ import annotations
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from fastapi import APIRouter, Depends, HTTPException

if TYPE_CHECKING:
    import asyncpg


class BasePlugin:
    """Base class all plugins must inherit from."""
    id: str = ""
    name: str = ""
    version: str = "1.0.0"
    dependencies: list[str] = []
    description: str = ""
    icon: str = "puzzle"

    def get_router(self) -> Optional[APIRouter]:
        """Returns FastAPI router with all plugin endpoints."""
        return None

    def get_tools(self) -> list[dict]:
        """Returns Gemini function calling tool declarations."""
        return []

    def get_tool_handlers(self) -> Dict[str, Any]:
        """Returns a dict mapping tool name -> async handler function."""
        return {}

    def get_system_prompt_section(self, config: dict) -> str:
        """Returns text to inject into the chatbot system prompt."""
        return ""

    async def on_install(self, db, instance_id: int):
        """Run schema creation, seed default data."""
        pass

    async def on_uninstall(self, db, instance_id: int):
        """Archive data (never delete)."""
        pass

    def get_frontend_routes(self) -> list[dict]:
        """Returns frontend route metadata for dynamic sidebar."""
        return []


def require_plugin(plugin_id: str):
    """FastAPI dependency that verifies a plugin is enabled for the instance."""
    from app.database import get_db

    async def checker(instance_id: int, db=Depends(get_db)):
        row = await db.fetchrow(
            "SELECT 1 FROM ancora_crm.instance_plugins "
            "WHERE instance_id = $1 AND plugin_id = $2 AND enabled = true",
            instance_id, plugin_id,
        )
        if not row:
            raise HTTPException(
                status_code=403,
                detail=f"Plugin '{plugin_id}' no habilitado para esta instancia",
            )
        return instance_id

    return Depends(checker)
