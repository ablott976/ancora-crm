"""Gemini function calling tools for the closures plugin."""
from datetime import date
import json
from google.genai import types


def _fd(name, description, parameters):
    """Shorthand for creating a FunctionDeclaration dict."""
    return types.FunctionDeclaration(
        name=name,
        description=description,
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties=parameters["properties"],
            required=parameters.get("required", []),
        ),
    )


CLOSURE_TOOLS = [
    _fd(
        "check_closures",
        "Indica si el negocio estara cerrado en una fecha concreta y muestra el motivo si existe.",
        {
            "properties": {
                "date": types.Schema(type=types.Type.STRING, description="Fecha en formato YYYY-MM-DD"),
            },
            "required": ["date"],
        },
    ),
    _fd(
        "list_upcoming_closures",
        "Lista los proximos cierres programados del negocio.",
        {
            "properties": {
                "limit": types.Schema(type=types.Type.INTEGER, description="Maximo de cierres a devolver"),
            },
            "required": [],
        },
    ),
]


async def _handle_check_closures(args: dict, ctx: dict) -> str:
    from app.plugins.closures.services import check_closures
    db = ctx["db"]
    instance_id = ctx["instance_id"]
    result = await check_closures(db, instance_id, date.fromisoformat(args["date"]))
    return json.dumps(result, default=str, ensure_ascii=False)


async def _handle_list_upcoming_closures(args: dict, ctx: dict) -> str:
    from app.plugins.closures.services import list_upcoming_closures
    db = ctx["db"]
    instance_id = ctx["instance_id"]
    limit = args.get("limit", 10)
    result = await list_upcoming_closures(db, instance_id, limit=limit)
    return json.dumps({"closures": result}, default=str, ensure_ascii=False)


CLOSURE_TOOL_HANDLERS = {
    "check_closures": _handle_check_closures,
    "list_upcoming_closures": _handle_list_upcoming_closures,
}
