"""Gemini tools for shift view."""
import json
from datetime import date
from google.genai import types


def _fd(name, desc, params):
    return types.FunctionDeclaration(name=name, description=desc,
        parameters=types.Schema(type=types.Type.OBJECT, properties=params["properties"], required=params.get("required", [])))


SHIFT_TOOLS = [
    _fd("get_professional_agenda", "Obtiene la agenda completa de un profesional para un día: turnos, citas y huecos.",
        {"properties": {
            "professional_id": types.Schema(type=types.Type.INTEGER, description="ID del profesional"),
            "date": types.Schema(type=types.Type.STRING, description="Fecha YYYY-MM-DD"),
        }, "required": ["professional_id", "date"]}),
]


async def _handle_agenda(args, ctx):
    from app.plugins.shift_view.services import get_day_agenda
    result = await get_day_agenda(ctx["db"], ctx["instance_id"], args["professional_id"], date.fromisoformat(args["date"]))
    return json.dumps(result, default=str, ensure_ascii=False)


SHIFT_TOOL_HANDLERS = {"get_professional_agenda": _handle_agenda}
