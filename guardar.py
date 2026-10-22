"""Persistencia del catastro: data/eventos.csv (fuente de verdad) y eventos.json."""

from __future__ import annotations

import csv
import os
import tempfile
from pathlib import Path

from comun import DATA, escribir_json, leer_json

CSV = DATA / "eventos.csv"
JSON = DATA / "eventos.json"

COLUMNAS = [
    "id",
    "fecha_publicacion",
    "fecha_deteccion",
    "titulo",
    "descripcion",
    "url",
    "fuente",
    "origen",
    "tipo_evento",
    "tipo_etiqueta",
    "region",
    "comuna",
    "lat",
    "lon",
    "keywords",
    "estado",
    "issue",
]

ESTADOS = {"nuevo", "confirmado", "descartado"}


def cargar_eventos(ruta: Path = CSV) -> list[dict]:
    """Lee el CSV del catastro; devuelve lista de dicts (vacia si no existe)."""
    if not ruta.exists():
        return []
    with open(ruta, encoding="utf-8-sig", newline="") as fh:
        lector = csv.DictReader(fh)
        return [dict(fila) for fila in lector]


def _ordenar(eventos: list[dict]) -> list[dict]:
    """Ordena por fecha de publicacion/deteccion descendente."""
    def clave(e: dict) -> str:
        return e.get("fecha_publicacion") or e.get("fecha_deteccion") or ""

    return sorted(eventos, key=clave, reverse=True)


def guardar_eventos(eventos: list[dict], csv_ruta: Path = CSV, json_ruta: Path = JSON) -> None:
    """Escribe CSV de forma atomica y regenera el JSON espejo."""
    eventos = _ordenar(eventos)
    for e in eventos:
        if e.get("estado") not in ESTADOS:
            e["estado"] = "nuevo"
        for col in COLUMNAS:
            e.setdefault(col, "")
        # Normaliza campos numericos vacios
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

    escribir_json(
        json_ruta,
        {"total": len(eventos), "eventos": eventos},
    )


def fusionar(existentes: list[dict], nuevos: list[dict]) -> list[dict]:
    """Agrega los nuevos al inicio y deduplica por id (gana el existente)."""
    ids = {e.get("id") for e in existentes}
    resultado = list(existentes)
    for e in nuevos:
        if e.get("id") not in ids:
            resultado.append(e)
            ids.add(e.get("id"))
    return _ordenar(resultado)


def leer_json_eventos(ruta: Path = JSON) -> list[dict]:
    datos = leer_json(ruta, {})
    return datos.get("eventos", []) if isinstance(datos, dict) else []
