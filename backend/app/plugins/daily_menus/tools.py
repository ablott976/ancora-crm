"""Gemini function calling tools for daily menus."""
import json
from datetime import date
from google.genai import types


def _fd(name, desc, params):
    return types.FunctionDeclaration(name=name, description=desc,
        parameters=types.Schema(type=types.Type.OBJECT, properties=params["properties"], required=params.get("required", [])))


DAILY_MENU_TOOLS = [
    _fd("get_todays_menu", "Muestra el menú del día de hoy con todos los platos y precio.",
        {"properties": {}, "required": []}),
    _fd("get_menu_for_date", "Muestra el menú de una fecha específica.",
        {"properties": {
            "date": types.Schema(type=types.Type.STRING, description="Fecha YYYY-MM-DD"),
        }, "required": ["date"]}),
]


async def _handle_today(args, ctx):
    from app.plugins.daily_menus.services import get_menu_for_date
    today = date.today()
    result = await get_menu_for_date(ctx["db"], ctx["instance_id"], today)
    if not result:
        return json.dumps({"available": False, "message": "No hay menú del día disponible hoy."}, ensure_ascii=False)
    return json.dumps({"available": True, "menu": result}, default=str, ensure_ascii=False)


async def _handle_by_date(args, ctx):
    from app.plugins.daily_menus.services import get_menu_for_date
    d = date.fromisoformat(args["date"])
    result = await get_menu_for_date(ctx["db"], ctx["instance_id"], d)
    if not result:
        return json.dumps({"available": False, "date": args["date"]}, ensure_ascii=False)
    return json.dumps({"available": True, "menu": result}, default=str, ensure_ascii=False)


DAILY_MENU_TOOL_HANDLERS = {"get_todays_menu": _handle_today, "get_menu_for_date": _handle_by_date}
