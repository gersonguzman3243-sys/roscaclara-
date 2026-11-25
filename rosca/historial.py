"""Historial local de las piezas revisadas. Vive en un archivo SQLite."""

from __future__ import annotations

import csv
import io
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


def _conectar(ruta: Path) -> sqlite3.Connection:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(ruta)
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS inspecciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT NOT NULL,
            veredicto TEXT NOT NULL,
            confianza REAL NOT NULL,
            puntaje REAL NOT NULL,
            tipo TEXT NOT NULL,
            explicacion TEXT NOT NULL,
            origen TEXT NOT NULL,
            nombre TEXT NOT NULL,
            miniatura BLOB NOT NULL
        )
        """
    )
    return conn


def agregar(
    ruta: Path,
    *,
    veredicto: str,
    confianza: float,
    puntaje: float,
    tipo: str,
    explicacion: str,
    origen: str,
    nombre: str,
    miniatura_jpeg: bytes,
) -> int:
    fecha = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with _conectar(ruta) as conn:
        cursor = conn.execute(
            """
            INSERT INTO inspecciones
                (fecha, veredicto, confianza, puntaje, tipo, explicacion, origen, nombre, miniatura)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (fecha, veredicto, confianza, puntaje, tipo, explicacion, origen, nombre, miniatura_jpeg),
        )
        return int(cursor.lastrowid)


def listar(ruta: Path) -> list[dict]:
    if not ruta.exists():
        return []
    with _conectar(ruta) as conn:
        filas = conn.execute(
            """
            SELECT id, fecha, veredicto, confianza, puntaje, tipo, explicacion, origen, nombre
            FROM inspecciones
            ORDER BY id DESC
            """
        ).fetchall()
    return [dict(fila) for fila in filas]


def resumen(ruta: Path) -> dict:
    items = listar(ruta)
    ok = sum(1 for item in items if item["veredicto"] == "OK")
    defectuosos = sum(1 for item in items if item["veredicto"] == "DEFECTUOSO")
    total = ok + defectuosos
    return {
        "total": total,
        "ok": ok,
        "defectuosos": defectuosos,
        "porcentaje_ok": round(100 * ok / total, 1) if total else 0,
        "porcentaje_defectuosos": round(100 * defectuosos / total, 1) if total else 0,
    }


def miniatura(ruta: Path, id_inspeccion: int) -> bytes | None:
    if not ruta.exists():
        return None
    with _conectar(ruta) as conn:
        fila = conn.execute(
            "SELECT miniatura FROM inspecciones WHERE id = ?",
            (id_inspeccion,),
        ).fetchone()
    if fila is None:
        return None
    return bytes(fila["miniatura"])


def vaciar(ruta: Path) -> None:
    if not ruta.exists():
        return
    with _conectar(ruta) as conn:
        conn.execute("DELETE FROM inspecciones")


def a_csv(ruta: Path) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        ["fecha", "nombre", "origen", "veredicto", "confianza_pct", "tipo", "explicacion"]
    )
    for item in reversed(listar(ruta)):
        writer.writerow(
            [
                item["fecha"],
                item["nombre"],
                item["origen"],
                item["veredicto"],
                round(float(item["confianza"]) * 100),
                item["tipo"],
                item["explicacion"],
            ]
        )
    return buffer.getvalue()
