"""
Availability engine — slot generation + verification.
Migrated from n8n workflows (Llenado Inicial, Mantenimiento Diario, Verificar Disponibilidad).
"""
import logging
import json
from datetime import date, datetime, timedelta, time
from typing import Optional

import asyncpg

from config import get_settings
from services.cierres import hora_blocked_by_turno

logger = logging.getLogger(__name__)
settings = get_settings()
_s = settings.db_schema

_pool: Optional[asyncpg.Pool] = None


def set_pool(pool: asyncpg.Pool) -> None:
    global _pool
    _pool = pool


DIAS_SEMANA = ['domingo', 'lunes', 'martes', 'miercoles', 'jueves', 'viernes', 'sabado']


# ---------------------------------------------------------------------------
# Get restaurant config
# ---------------------------------------------------------------------------
async def get_config() -> dict:
    async with _pool.acquire() as conn:
        row = await conn.fetchrow(f"SELECT * FROM {_s}.configuracion LIMIT 1")
        if not row:
            return {}
        result = dict(row)
        if isinstance(result.get("horarios_semana"), str):
            result["horarios_semana"] = json.loads(result["horarios_semana"])
        return result


async def get_mesas_activas() -> list[dict]:
    async with _pool.acquire() as conn:
        rows = await conn.fetch(
            f"SELECT * FROM {_s}.mesas WHERE activa = TRUE ORDER BY id"
        )
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Check if date is closed
# ---------------------------------------------------------------------------
async def _is_closed(d: date, config: dict) -> bool:
    """Check holidays + closed days."""
    # Check holidays
    async with _pool.acquire() as conn:
        is_holiday = await conn.fetchval(
            f"SELECT EXISTS(SELECT 1 FROM {_s}.festivos WHERE fecha = $1)",
            d,
        )
    if is_holiday:
        return True

    # Check fixed closed days (DD/MM)
    dia_str = f"{d.day:02d}/{d.month:02d}"
    cerrados_fijos = [x.strip() for x in (config.get("dias_cerrados_fijos") or "").split(",") if x.strip()]
    if dia_str in cerrados_fijos:
        return True

    # Check specific closed days (DD/MM/YYYY)
    fecha_str = f"{d.day:02d}/{d.month:02d}/{d.year}"
    cerrados_esp = [x.strip() for x in (config.get("dias_cerrados_especificos") or "").split(",") if x.strip()]
    if fecha_str in cerrados_esp:
        return True

    # Check weekly schedule
    dia_semana = DIAS_SEMANA[d.weekday() + 1 if d.weekday() < 6 else 0]  # Python weekday → our mapping
    horarios = config.get("horarios_semana", {})
    if not horarios.get(dia_semana):
        return True

    return False


# ---------------------------------------------------------------------------
# Generate slots for a single day
# ---------------------------------------------------------------------------
def _generate_day_slots(d: date, config: dict, mesas: list[dict]) -> list[dict]:
    """Generate 30-min slots for all active tables on a given day."""
    dia_idx = d.weekday()  # 0=Mon, 6=Sun
    # Map Python weekday to our naming
    dia_map = {0: 'lunes', 1: 'martes', 2: 'miercoles', 3: 'jueves', 4: 'viernes', 5: 'sabado', 6: 'domingo'}
    dia_nombre = dia_map[dia_idx]

    horarios = config.get("horarios_semana", {})
    config_dia = horarios.get(dia_nombre)
    if not config_dia:
        return []

    slots = []
    fecha_str = d.isoformat()

    for mesa in mesas:
        mesa_id = mesa["id"]

        for turno_key in ["comidas", "cenas"]:
            turno = config_dia.get(turno_key)
            if not turno:
                continue

            h_inicio, m_inicio = map(int, turno["inicio"].split(":"))
            h_fin, m_fin = map(int, turno["fin"].split(":"))

            # Handle midnight crossing (e.g., fin = "02:00")
            if h_fin < h_inicio:
                h_fin += 24

            hora_actual = h_inicio * 60 + m_inicio
            hora_fin = h_fin * 60 + m_fin

            while hora_actual < hora_fin - 29:  # Need at least 30 min
                h = (hora_actual // 60) % 24
                m = hora_actual % 60
                hora_slot = f"{h:02d}:{m:02d}"

                slots.append({
                    "fecha": fecha_str,
                    "hora_disponible": hora_slot,
                    "id_mesa": mesa_id,
                    "estado": "Disponible",
                })

                hora_actual += 30

    return slots


# ---------------------------------------------------------------------------
# Initial fill (60 days)
# ---------------------------------------------------------------------------
async def llenar_inicial():
    """Generate slots for the next 60 days."""
    config = await get_config()
    mesas = await get_mesas_activas()
    hoy = date.today()
    total = 0

    async with _pool.acquire() as conn:
        for i in range(settings.max_reservation_days):
            d = hoy + timedelta(days=i)
            if await _is_closed(d, config):
                continue

            slots = _generate_day_slots(d, config, mesas)
            for slot in slots:
                await conn.execute(
                    f"""INSERT INTO {_s}.disponibilidad_mesas (fecha, hora_disponible, id_mesa, estado)
                        VALUES ($1, $2, $3, $4)
                        ON CONFLICT (fecha, hora_disponible, id_mesa) DO NOTHING""",
                    date.fromisoformat(slot["fecha"]),
                    time.fromisoformat(slot["hora_disponible"]),
                    slot["id_mesa"],
                    slot["estado"],
                )
            total += len(slots)

    logger.info(f"Initial fill complete: {total} slots generated")
    return total


# ---------------------------------------------------------------------------
# Daily maintenance (add day +61, clean old)
# ---------------------------------------------------------------------------
async def mantenimiento_diario():
    """Add slots for day +61 and delete slots older than 30 days."""
    config = await get_config()
    mesas = await get_mesas_activas()
    hoy = date.today()

    # Generate day +61
    fecha_futuro = hoy + timedelta(days=settings.max_reservation_days + 1)
    slots_creados = 0

    if not await _is_closed(fecha_futuro, config):
        slots = _generate_day_slots(fecha_futuro, config, mesas)
        async with _pool.acquire() as conn:
            for slot in slots:
                await conn.execute(
                    f"""INSERT INTO {_s}.disponibilidad_mesas (fecha, hora_disponible, id_mesa, estado)
                        VALUES ($1, $2, $3, $4)
                        ON CONFLICT (fecha, hora_disponible, id_mesa) DO NOTHING""",
                    date.fromisoformat(slot["fecha"]),
                    time.fromisoformat(slot["hora_disponible"]),
                    slot["id_mesa"],
                    slot["estado"],
                )
            slots_creados = len(slots)

    # Delete old slots (>30 days ago)
    async with _pool.acquire() as conn:
        result = await conn.execute(
            f"DELETE FROM {_s}.disponibilidad_mesas WHERE fecha < $1",
            hoy - timedelta(days=30),
        )

    logger.info(f"Daily maintenance: {slots_creados} slots created, old slots cleaned")
    return slots_creados


# ---------------------------------------------------------------------------
# Verify availability
# ---------------------------------------------------------------------------
async def verificar_disponibilidad(
    fecha: str,
    personas: int,
    hora: Optional[str] = None,
    call_id: Optional[str] = None,
) -> dict:
    """
    Check availability for a date.
    Without hora: returns all available times.
    With hora: checks specific time and blocks slots temporarily.
    """
    # Convert string date to date object for asyncpg
    fecha_obj = date.fromisoformat(fecha) if isinstance(fecha, str) else fecha

    # Check cierres table (puntual + semanal closures)
    async with _pool.acquire() as conn:
        cierre_rows = await conn.fetch(
            f"""SELECT tipo, recurrencia, fecha, dia_semana, turno FROM {_s}.cierres
                WHERE activo = TRUE"""
        )
    # dia_semana convention: 0=domingo, 1=lunes, ..., 6=sabado (JS-style)
    # Python weekday(): 0=Mon..6=Sun -> convert: (weekday+1)%7
    dia_semana_js = (fecha_obj.weekday() + 1) % 7

    # Collect partial-turno closures that apply to this date
    active_turno_closures: list[str] = []

    for cr in cierre_rows:
        turno = cr.get("turno") or "completo"
        matches = (
            (cr["recurrencia"] == "puntual" and cr["fecha"] == fecha_obj) or
            (cr["recurrencia"] == "semanal" and cr["dia_semana"] == dia_semana_js)
        )
        if not matches:
            continue

        if turno == "completo":
            if not call_id:
                import random, string as string_mod
                call_id = f"session_{int(datetime.now().timestamp())}_{random.choices(string_mod.ascii_lowercase, k=6)[0]}"
            return {
                "disponible": False,
                "restaurante_cerrado": True,
                "call_id_temporal": call_id,
                "mensaje": f"El restaurante esta cerrado el {fecha}.",
            }
        else:
            active_turno_closures.append(turno)

    # Release previous temp locks for this session
    if call_id:
        async with _pool.acquire() as conn:
            await conn.execute(
                f"""UPDATE {_s}.disponibilidad_mesas
                    SET estado = 'Disponible', call_id_temporal = NULL, locked_at = NULL
                    WHERE call_id_temporal = $1 AND estado = 'Temporal'""",
                call_id,
            )

    # Generate new call_id if needed
    if not call_id:
        import random, string
        call_id = f"session_{int(datetime.now().timestamp())}_{random.choices(string.ascii_lowercase, k=6)[0]}"

    # Fetch available slots for the day
    async with _pool.acquire() as conn:
        rows = await conn.fetch(
            f"""SELECT d.id, d.fecha, d.id_mesa, d.hora_disponible, d.estado, d.id_reserva,
                       d.call_id_temporal, m.sillas
                FROM {_s}.disponibilidad_mesas d
                INNER JOIN {_s}.mesas m ON d.id_mesa = m.id
                WHERE d.fecha = $1
                  AND m.activa = TRUE
                  AND (d.estado = 'Disponible' OR (d.estado = 'Temporal' AND d.call_id_temporal = $2))
                ORDER BY d.id_mesa, d.hora_disponible""",
            fecha_obj, call_id,
        )

    slots = [dict(r) for r in rows]

    # Filter out slots blocked by partial-turno closures
    if active_turno_closures:
        slots = [
            s for s in slots
            if not any(
                hora_blocked_by_turno(str(s["hora_disponible"])[:5], t)
                for t in active_turno_closures
            )
        ]

    if not slots:
        return {
            "disponible": False,
            "restaurante_cerrado": True,
            "call_id_temporal": call_id,
            "mensaje": f"No hay disponibilidad para el {fecha}.",
        }

    # Group by table
    mesas = {}
    for s in slots:
        mid = s["id_mesa"]
        if mid not in mesas:
            mesas[mid] = {"sillas": s["sillas"], "slots": []}
        mesas[mid]["slots"].append(s)

    if not hora:
        # Return all available times
        disponibilidades = []
        for mesa_id, mesa_data in sorted(mesas.items()):
            if mesa_data["sillas"] < personas:
                continue
            for s in mesa_data["slots"]:
                h = str(s["hora_disponible"])[:5]
                if not any(d["hora"] == h for d in disponibilidades):
                    disponibilidades.append({
                        "hora": h,
                        "mesa_id": mesa_id,
                        "slots_ids": [s["id"]],
                    })

        return {
            "disponible": len(disponibilidades) > 0,
            "modo": "todas_disponibilidades",
            "fecha": fecha,
            "personas": personas,
            "call_id_temporal": call_id,
            "total_horarios": len(disponibilidades),
            "disponibilidades": disponibilidades,
        }

    # Check specific time — find best table and block
    def hora_a_minutos(h: str) -> int:
        parts = h.split(":")
        return int(parts[0]) * 60 + int(parts[1])

    hora_min = hora_a_minutos(hora)
    slots_necesarios = 4  # Default 2 hours

    # Sort tables by capacity (smallest sufficient first)
    mesas_validas = sorted(
        [(mid, md) for mid, md in mesas.items() if md["sillas"] >= personas],
        key=lambda x: x[1]["sillas"],
    )

    for mesa_id, mesa_data in mesas_validas:
        consecutivos = []
        for i in range(slots_necesarios):
            hora_buscada = f"{((hora_min + i * 30) // 60) % 24:02d}:{(hora_min + i * 30) % 60:02d}"
            found = next(
                (s for s in mesa_data["slots"] if str(s["hora_disponible"])[:5] == hora_buscada),
                None,
            )
            if found:
                consecutivos.append(found)
            else:
                break

        if len(consecutivos) == slots_necesarios:
            # Block slots
            async with _pool.acquire() as conn:
                for s in consecutivos:
                    await conn.execute(
                        f"""UPDATE {_s}.disponibilidad_mesas
                            SET estado = 'Temporal', call_id_temporal = $1, locked_at = NOW()
                            WHERE id = $2 AND (estado = 'Disponible' OR call_id_temporal = $1)""",
                        call_id, s["id"],
                    )

            return {
                "disponible": True,
                "slots_bloqueados": True,
                "mesa_id": mesa_id,
                "slots_ids": [s["id"] for s in consecutivos],
                "fecha": fecha,
                "hora": hora,
                "personas": personas,
                "call_id_temporal": call_id,
                "sillas_mesa": mesa_data["sillas"],
            }

    return {
        "disponible": False,
        "restaurante_cerrado": False,
        "call_id_temporal": call_id,
        "fecha": fecha,
        "hora_solicitada": hora,
        "personas": personas,
        "mensaje": f"No hay mesa disponible a las {hora} para {personas} personas.",
    }
