"""Gemini function calling tools for owner agent."""
import json
from google.genai import types


def _fd(name, desc, params):
    return types.FunctionDeclaration(name=name, description=desc,
        parameters=types.Schema(type=types.Type.OBJECT, properties=params["properties"], required=params.get("required", [])))


OWNER_TOOLS = [
    _fd("get_business_summary", "Obtiene un resumen del día: conversaciones, mensajes, reservas nuevas.",
        {"properties": {
            "date": types.Schema(type=types.Type.STRING, description="Fecha YYYY-MM-DD (por defecto hoy)"),
        }, "required": []}),
]


async def _handle_summary(args, ctx):
    from app.plugins.owner_agent.services import get_daily_summary
    from datetime import date as d
    target = d.fromisoformat(args["date"]) if args.get("date") else None
    result = await get_daily_summary(ctx["db"], ctx["instance_id"], target)
    return json.dumps(result, default=str, ensure_ascii=False)


OWNER_TOOL_HANDLERS = {"get_business_summary": _handle_summary}
