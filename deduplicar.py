"""Deduplicacion persistente de eventos (estado en data/vistos.json)."""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from comun import RAIZ, normalizar

STOPWORDS = {
    "para", "como", "tras", "sobre", "entre", "desde", "hasta", "donde", "cuando",
    "este", "esta", "estos", "estas", "unos", "unas", "ante", "bajo", "contra",
    "segun", "durante", "mediante", "tiene", "tienen", "sera", "seran", "puede",
    "pueden", "tras", "aunque", "porque", "mientras", "todo", "toda", "todos",
    "todas", "otro", "otra", "otros", "otras", "hace", "hacia", "desde",
}

VISTOS = RAIZ / "data" / "vistos.json"


def titulo_canonico(titulo: str) -> str:
    """Normaliza el titulo para comparar entre medios.

    Quita sufijos tipicos de agregadores (" - Medio.cl", " | Medio") y
    numeros de seccion, y colapsa espacios.
    """
    t = normalizar(titulo)
    t = re.sub(r"\s*[-|]\s*[a-z0-9 .]+$", "", t)
    return t.strip()


def dominio(url: str) -> str:
    try:
        host = urlparse(url).netloc.lower()
        return host[4:] if host.startswith("www.") else host
    except ValueError:
        return ""


def clave_registro(registro: dict) -> str:
    """Clave estable a partir del titulo canonico y el dominio."""
    base = titulo_canonico(registro.get("titulo", "")) or (registro.get("url") or "")
    base = f"{base}|{dominio(registro.get('url', ''))}"
    return hashlib.sha1(base.encode("utf-8")).hexdigest()[:12]


def cargar_vistos(ruta: Path = VISTOS) -> dict:
    from comun import leer_json

    datos = leer_json(ruta, {})
    return datos.get("claves", datos if isinstance(datos, dict) else {})


def guardar_vistos(claves: dict, ruta: Path = VISTOS, actualizado: str = "") -> None:
    from comun import escribir_json

    escribir_json(ruta, {"actualizado": actualizado, "total": len(claves), "claves": claves})


def filtrar_nuevos(registros: list[dict], vistos: dict) -> list[dict]:
    """Devuelve solo los registros cuya clave no esta en vistos."""
    nuevos = []
    for reg in registros:
        if clave_registro(reg) not in vistos:
            nuevos.append(reg)
    return nuevos


def palabras_clave(titulo: str) -> set[str]:
    return {p for p in normalizar(titulo).split() if len(p) >= 4 and p not in STOPWORDS}


def jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _fecha(valor) -> datetime | None:
    if not valor:
        return None
    if isinstance(valor, datetime):
        dt = valor
    else:
        try:
            dt = datetime.fromisoformat(str(valor).replace("Z", "+00:00"))
        except ValueError:
            return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _mismo_lugar(a: dict, b: dict) -> bool:
    for campo in ("comuna", "region"):
        va, vb = (a.get(campo) or "").strip().lower(), (b.get(campo) or "").strip().lower()
        if va and va == vb:
            return True
    return False


def es_duplicado(
    registro: dict,
    comparar_con: list[dict],
    umbral: float = 0.62,
    dias: int = 4,
    umbral_evento: float = 0.20,
    umbral_sin_lugar: float = 0.35,
) -> bool:
    """Detecta la misma noticia publicada por varios medios.

    Dos criterios:
    1) titulos casi iguales (Jaccard >= umbral);
    2) mismo evento: mismo tipo y localidad, fecha a <= 1 dia y al menos
       dos palabras de contenido en comun (los medios titulan muy distinto
       el mismo hecho).
    """
    pal = palabras_clave(registro.get("titulo", ""))
    if not pal:
        return False
    f1 = _fecha(registro.get("publicado") or registro.get("fecha_publicacion"))
    for otro in comparar_con:
        f2 = _fecha(otro.get("fecha_publicacion") or otro.get("fecha_deteccion"))
        diferencia = abs((f1 - f2).total_seconds()) if (f1 and f2) else None
        if diferencia is not None and diferencia > dias * 86400:
            continue

        sim = jaccard(pal, palabras_clave(otro.get("titulo", "")))
        if sim >= umbral:
            return True

        mismo_tipo = (registro.get("tipo_evento") or "") == (otro.get("tipo_evento") or "")
        mismo_dia = diferencia is None or diferencia <= 86400
        if mismo_tipo and mismo_dia and sim >= umbral_evento and _mismo_lugar(registro, otro):
            return True
        # Mismo evento aunque no se haya detectado la localidad (noticias que
        # solo nombran el paraje: Portillo, una quebrada, un sector rural).
        if mismo_tipo and mismo_dia and sim >= umbral_sin_lugar:
            return True
    return False
