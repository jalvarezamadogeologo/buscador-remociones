"""Agrupacion de noticias en eventos y seleccion de las primeras fuentes.

Un evento es un hecho (tipo + lugar + fecha). De todas las noticias que lo
reportan se conservan como maximo 3 fuentes, ordenadas por fecha de publicacion
ascendente: las primeras que reportaron el hecho.
"""

from __future__ import annotations

from datetime import datetime, timezone

from comun import a_iso
from deduplicar import jaccard, palabras_clave

MAX_FUENTES = 3
DIAS_MISMO_EVENTO = 2
UMBRAL_TITULO_SIN_LUGAR = 0.50

COLUMNAS = [
    "id",
    "fecha_publicacion",
    "fecha_deteccion",
    "titulo",
    "tipo_evento",
    "tipo_etiqueta",
    "region",
    "comuna",
    "lat",
    "lon",
    "fuente_1",
    "url_1",
    "fecha_1",
    "fuente_2",
    "url_2",
    "fecha_2",
    "fuente_3",
    "url_3",
    "fecha_3",
    "estado",
    "issue",
]


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


def _lugar(region: str | None, comuna: str | None) -> tuple[str, str]:
    return (region or "", comuna or "")


def fuentes(evento: dict) -> list[dict]:
    """Lista de fuentes del evento (medio, url, fecha)."""
    salida = []
    for i in (1, 2, 3):
        medio = evento.get(f"fuente_{i}") or ""
        url = evento.get(f"url_{i}") or ""
        fecha = evento.get(f"fecha_{i}") or ""
        if medio or url:
            salida.append({"medio": medio, "url": url, "fecha": fecha})
    return salida


def etiqueta_evento(evento: dict) -> str:
    """Tipo de remocion + lugar (comuna)."""
    lugar = evento.get("comuna") or evento.get("region") or "Chile"
    tipo = evento.get("tipo_etiqueta") or evento.get("tipo_evento") or "Remocion en masa"
    return f"{tipo} en {lugar}"


def buscar_evento(eventos: list[dict], noticia: dict) -> dict | None:
    """Busca el evento al que pertenece una noticia (tipo + lugar + fecha)."""
    f1 = _fecha(noticia.get("publicado") or noticia.get("fecha_publicacion"))
    for evento in eventos:
        if evento.get("tipo_evento") != noticia.get("tipo_evento"):
            continue

        f2 = _fecha(evento.get("fecha_publicacion"))
        if f1 and f2 and abs((f1 - f2).total_seconds()) > DIAS_MISMO_EVENTO * 86400:
            continue

        r1, c1 = _lugar(evento.get("region"), evento.get("comuna"))
        r2, c2 = _lugar(noticia.get("region"), noticia.get("comuna"))
        if (r1 or c1) and (r2 or c2):
            if (r1, c1) != (r2, c2):
                continue
        else:
            sim = jaccard(
                palabras_clave(noticia.get("titulo", "")),
                palabras_clave(evento.get("titulo", "")),
            )
            if sim < UMBRAL_TITULO_SIN_LUGAR:
                continue
        return evento
    return None


def agregar_fuente(evento: dict, noticia: dict) -> bool:
    """Agrega una noticia como fuente del evento. Devuelve True si era nueva."""
    actuales = fuentes(evento)
    url = noticia.get("url", "")
    if url and any(f["url"] == url for f in actuales):
        return False

    actuales.append(
        {
            "medio": noticia.get("fuente", ""),
            "url": url,
            "fecha": a_iso(noticia.get("publicado")),
        }
    )
    # Las 3 primeras que reportaron: orden por fecha ascendente.
    actuales.sort(key=lambda f: f["fecha"] or "9999")
    actuales = actuales[:MAX_FUENTES]

    for i in (1, 2, 3):
        fuente = actuales[i - 1] if i <= len(actuales) else {"medio": "", "url": "", "fecha": ""}
        evento[f"fuente_{i}"] = fuente["medio"]
        evento[f"url_{i}"] = fuente["url"]
        evento[f"fecha_{i}"] = fuente["fecha"]

    fechas = [f["fecha"] for f in actuales if f["fecha"]]
    if fechas:
        evento["fecha_publicacion"] = min(fechas)
    return True


def crear_evento(noticia: dict, deteccion: str, clave: str) -> dict:
    """Crea un evento nuevo a partir de la primera noticia detectada."""
    evento = {columna: "" for columna in COLUMNAS}
    evento.update(
        {
            "id": clave,
            "fecha_publicacion": a_iso(noticia.get("publicado")),
            "fecha_deteccion": deteccion,
            "titulo": noticia.get("titulo", ""),
            "tipo_evento": noticia.get("tipo_evento", ""),
            "tipo_etiqueta": noticia.get("tipo_etiqueta", ""),
            "region": noticia.get("region", ""),
            "comuna": noticia.get("comuna", ""),
            "estado": "nuevo",
        }
    )
    agregar_fuente(evento, noticia)
    return evento
