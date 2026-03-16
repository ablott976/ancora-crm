"""
Reservation engine — CRUD for reservations.
Migrated from n8n Tool workflows (Buscar/Crear/Modificar/Cancelar).
"""
import logging
from datetime import date, time, datetime
from typing import Optional

import asyncpg

from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()
_s = settings.db_schema

_pool: Optional[asyncpg.Pool] = None


def set_pool(pool: asyncpg.Pool) -> None:
    global _pool
    _pool = pool


# ---------------------------------------------------------------------------
# State machine
# ---------------------------------------------------------------------------
VALID_TRANSITIONS: dict[str, set[str]] = {
    "Temporal":   {"Pendiente", "Cancelada"},
    "Pendiente":  {"Confirmada", "Reservada", "Cancelada"},
    "Reservada":  {"Confirmada", "Pendiente", "Cancelada", "Completada", "No-show"},
    "Confirmada": {"Pendiente", "Cancelada", "Completada", "No-show"},
    "Cancelada":  set(),
    "Completada": set(),
    "No-show":    set(),
}


def validate_transition(current: str, new: str) -> None:
    """Raise ValueError if the transition current → new is not allowed."""
    allowed = VALID_TRANSITIONS.get(current)
    if allowed is None:
        raise ValueError(f"Estado desconocido: {current!r}")
    if new not in allowed:
        terminal = not allowed
        detail = "estado terminal" if terminal else f"permitidos: {sorted(allowed)}"
        raise ValueError(
            f"Cannot transition from {current!r} to {new!r} ({detail})"
        )


# ---------------------------------------------------------------------------
# Search reservations by phone
# ---------------------------------------------------------------------------
async def buscar_por_telefono(telefono: str) -> list[dict]:
    """Find active reservations for a phone number."""
    # Strip country prefix
    telefono = telefono.strip()
    if telefono.startswith("+34") and len(telefono) == 12:
        telefono = telefono[3:]
    elif telefono.startswith("34") and len(telefono) == 11:
        telefono = telefono[2:]

    async with _pool.acquire() as conn:
        rows = await conn.fetch(
            f"""SELECT id, id_reserva, fecha, hora, id_mesa, personas,
                       nombre, telefono, estado, observaciones
                FROM {_s}.reservas
                WHERE telefono = $1
                  AND estado IN ('Temporal', 'Pendiente', 'Confirmada', 'Reservada')
                ORDER BY fecha DESC, hora DESC""",
            telefono,
        )
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Create reservation
# ---------------------------------------------------------------------------
async def crear_reserva(
    fecha: str,
    hora: str,
    personas: int,
    telefono: str,
    nombre: str,
    mesa_id: int,
    slots_ids: list[int],
    call_id_temporal: Optional[str] = None,
    observaciones: str = "",
) -> dict:
    """Create a reservation and link slots."""
    if personas < 1:
        return {"error": "El número de personas debe ser al menos 1"}
    telefono = telefono.strip()
    if telefono.startswith("+34") and len(telefono) == 12:
        telefono = telefono[3:]
    elif telefono.startswith("34") and len(telefono) == 11:
        telefono = telefono[2:]

    # Ensure proper types for asyncpg
    from datetime import date as _date, time as _time
    if isinstance(fecha, str):
        fecha = _date.fromisoformat(fecha)
    if isinstance(hora, str):
        h, m = hora.split(":")
        hora = _time(int(h), int(m))

    async with _pool.acquire() as conn:
        async with conn.transaction():
            # Lock slots with SELECT FOR UPDATE to prevent race conditions
            locked_slots = await conn.fetch(
                f"""SELECT id, estado FROM {_s}.disponibilidad_mesas
                    WHERE id = ANY($1::int[])
                    FOR UPDATE""",
                slots_ids,
            )

            # Verify all slots are still in 'Temporal' state
            locked_ids = {r["id"] for r in locked_slots}
            missing = set(slots_ids) - locked_ids
            not_temporal = [r for r in locked_slots if r["estado"] != "Temporal"]
            if missing or not_temporal:
                return {
                    "error": "Los slots ya no están disponibles. Por favor, busca disponibilidad de nuevo.",
                    "exito": False,
                }

            # Insert reservation
            row = await conn.fetchrow(
                f"""INSERT INTO {_s}.reservas
                    (fecha, hora, id_mesa, personas, nombre, telefono, estado, observaciones, origen)
                    VALUES ($1, $2, $3, $4, $5, $6, 'Pendiente', $7, 'WhatsApp Agente')
                    RETURNING id, id_reserva""",
                fecha, hora, mesa_id, personas, nombre, telefono, observaciones,
            )
            reserva_id = row["id"]
            codigo = row["id_reserva"]

            # Link slots
            for slot_id in slots_ids:
                await conn.execute(
                    f"""UPDATE {_s}.disponibilidad_mesas
                        SET estado = 'Reservada', id_reserva = $1, call_id_temporal = NULL
                        WHERE id = $2 AND estado = 'Temporal'""",
                    reserva_id, slot_id,
                )

    return {"id": reserva_id, "codigo_reserva": codigo, "exito": True}


# ---------------------------------------------------------------------------
# Cancel reservation
# ---------------------------------------------------------------------------
async def cancelar_reserva(codigo_reserva: str) -> dict:
    """Cancel a reservation and free its slots."""
    async with _pool.acquire() as conn:
        async with conn.transaction():
            # Find reservation
            row = await conn.fetchrow(
                f"SELECT * FROM {_s}.reservas WHERE id_reserva = $1",
                codigo_reserva,
            )
            if not row:
                return {"exito": False, "mensaje": "Reserva no encontrada"}

            validate_transition(row["estado"], "Cancelada")

            # Free slots
            await conn.execute(
                f"""UPDATE {_s}.disponibilidad_mesas
                    SET estado = 'Disponible', id_reserva = NULL
                    WHERE id_reserva = $1""",
                row["id"],
            )

            # Mark cancelled
            await conn.execute(
                f"""UPDATE {_s}.reservas
                    SET estado = 'Cancelada', fecha_modificacion = NOW()
                    WHERE id = $1""",
                row["id"],
            )

    return {"exito": True, "reserva": dict(row)}


# ---------------------------------------------------------------------------
# Confirm reservation
# ---------------------------------------------------------------------------
async def confirmar_reserva(reserva_id: int) -> dict:
    """Confirm a pending reservation."""
    async with _pool.acquire() as conn:
        async with conn.transaction():
            current = await conn.fetchrow(
                f"SELECT id, estado FROM {_s}.reservas WHERE id = $1",
                reserva_id,
            )
            if not current:
                return {"exito": False, "mensaje": "Reserva no encontrada"}

            validate_transition(current["estado"], "Confirmada")

            row = await conn.fetchrow(
                f"""UPDATE {_s}.reservas SET estado = 'Confirmada', fecha_modificacion = NOW()
                    WHERE id = $1 RETURNING *""",
                reserva_id,
            )
            await conn.execute(
                f"""UPDATE {_s}.disponibilidad_mesas
                    SET estado = 'Confirmada' WHERE id_reserva = $1""",
                reserva_id,
            )
    return {"exito": bool(row)}


# ---------------------------------------------------------------------------
# Modify reservation
# ---------------------------------------------------------------------------
async def modificar_reserva(
    codigo_reserva: str,
    fecha: Optional[str] = None,
    hora: Optional[str] = None,
    personas: Optional[int] = None,
    observaciones: Optional[str] = None,
) -> dict:
    """Modify an existing reservation. Slot reassignment handled separately."""
    async with _pool.acquire() as conn:
        row = await conn.fetchrow(
            f"SELECT * FROM {_s}.reservas WHERE id_reserva = $1",
            codigo_reserva,
        )
        if not row:
            return {"exito": False, "mensaje": "Reserva no encontrada"}

        updates = []
        params = []
        idx = 1

        if fecha:
            updates.append(f"fecha = ${idx}::date")
            params.append(fecha)
            idx += 1
        if hora:
            updates.append(f"hora = ${idx}::time")
            params.append(hora)
            idx += 1
        if personas is not None:
            updates.append(f"personas = ${idx}")
            params.append(personas)
            idx += 1
        if observaciones is not None:
            updates.append(f"observaciones = ${idx}")
            params.append(observaciones)
            idx += 1

        updates.append("fecha_modificacion = NOW()")
        params.append(row["id"])

        await conn.execute(
            f"""UPDATE {_s}.reservas SET {', '.join(updates)}
                WHERE id = ${idx}""",
            *params,
        )

    return {"exito": True, "reserva_anterior": dict(row)}
