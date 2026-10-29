"""Persistencia del catastro: data/eventos.csv (fuente de verdad) y eventos.json.

Cada fila es un evento agrupado con hasta 3 fuentes (fuente_1..fuente_3).
"""

from __future__ import annotations

import csv
import os
import tempfile
from pathlib import Path

from agrupar import COLUMNAS
from comun import DATA, escribir_json, leer_json

CSV = DATA / "eventos.csv"
JSON = DATA / "eventos.json"

ESTADOS = {"nuevo", "confirmado", "descartado"}
CONFIANZAS = {"alta", "baja"}


def cargar_eventos(ruta: Path = CSV) -> list[dict]:
    """Lee el CSV del catastro; devuelve lista de dicts (vacia si no existe)."""
    if not ruta.exists():
        return []
    with open(ruta, encoding="utf-8-sig", newline="") as fh:
        lector = csv.DictReader(fh)
        filas = [dict(fila) for fila in lector]
    for fila in filas:
        # Columnas agregadas el 2026-10-29: los catastros antiguos no las traen.
        if fila.get("confianza") not in CONFIANZAS:
            fila["confianza"] = "alta"
        fila.setdefault("motivo", "")
    return filas


def ordenar_eventos(eventos: list[dict]) -> list[dict]:
    """Ordena por fecha de publicacion descendente."""

    def clave(e: dict) -> str:
        return e.get("fecha_publicacion") or e.get("fecha_deteccion") or ""

    return sorted(eventos, key=clave, reverse=True)


def guardar_eventos(eventos: list[dict], csv_ruta: Path = CSV, json_ruta: Path = JSON) -> None:
    """Escribe CSV de forma atomica y regenera el JSON espejo."""
    eventos = ordenar_eventos(eventos)
    for e in eventos:
        if e.get("estado") not in ESTADOS:
            e["estado"] = "nuevo"
        if e.get("confianza") not in CONFIANZAS:
            e["confianza"] = "alta"
        for col in COLUMNAS:
            e.setdefault(col, "")
        for col in ("lat", "lon"):
            if e.get(col) in ("None", None):
                e[col] = ""

    csv_ruta.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(csv_ruta.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8-sig", newline="") as fh:
            escritor = csv.DictWriter(fh, fieldnames=COLUMNAS, extrasaction="ignore")
            escritor.writeheader()
            for e in eventos:
                escritor.writerow({c: e.get(c, "") for c in COLUMNAS})
        os.replace(tmp, csv_ruta)
    except Exception:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise

    escribir_json(json_ruta, {"total": len(eventos), "eventos": eventos})


def leer_json_eventos(ruta: Path = JSON) -> list[dict]:
    datos = leer_json(ruta, {})
    return datos.get("eventos", []) if isinstance(datos, dict) else []
