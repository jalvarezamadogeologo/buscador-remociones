"""Busqueda por keywords en X, Instagram y Facebook via Google News RSS.

Google News acepta `site:` en la consulta y devuelve las publicaciones indexadas
de cada red, con la fuente identificada (X, Instagram, Facebook). No requiere
API keys. La cobertura depende de lo que Google indexe de cada red.
"""

from __future__ import annotations

from datetime import datetime, timezone

import feedparser
import requests

import dominios
from comun import limpiar_html, limpiar_titulo, log, normalizar

URL = "https://news.google.com/rss/search"
TIMEOUT = 30
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36 buscador-remociones/1.0"
)

REDES = {
    "x": {"site": "site:x.com", "nombre": "X", "fuentes": {"x", "twitter"}},
    "instagram": {"site": "site:instagram.com", "nombre": "Instagram", "fuentes": {"instagram"}},
    "facebook": {"site": "site:facebook.com", "nombre": "Facebook", "fuentes": {"facebook"}},
}


def _terminos(config: dict) -> list[str]:
    terminos: list[str] = []
    for tipo in (config.get("tipos_evento") or {}).values():
        for clave in tipo.get("claves", []):
            if " " not in clave and clave not in terminos:
                terminos.append(clave)
    maximo = int((config.get("consulta") or {}).get("max_terminos", 10))
    return terminos[:maximo]


def _query(config: dict, red: str, lookback_horas: int) -> str:
    terminos = _terminos(config)
    if not terminos:
        return ""
    dias = max(1, round(lookback_horas / 24))
    return f"({' OR '.join(terminos)}) {REDES[red]['site']} when:{dias}d"


def _fuente_feed(entry) -> str:
    fuente = entry.get("source")
    if isinstance(fuente, dict):
        return str(fuente.get("title") or "")
    return str(fuente or "")


def _fecha(entry) -> datetime | None:
    struct = entry.get("published_parsed") or entry.get("updated_parsed")
    if not struct:
        return None
    try:
        return datetime(*struct[:6], tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None


def _limpiar_red(titulo: str, red: str) -> str:
    t = titulo.strip()
    sufijos = (f" - {REDES[red]['nombre']}", " - X", " - Twitter", " - Instagram", " - Facebook")
    for sufijo in sufijos:
        if t.endswith(sufijo):
            return t[: -len(sufijo)].strip()
    return t


def buscar_redes(
    config: dict, lookback_horas: int = 24, redes: list[str] | None = None
) -> list[dict]:
    """Consulta Google News con `site:` para cada red activa."""
    cfg = config.get("redes") or {}
    if not cfg.get("activa", True):
        return []

    activas = redes or cfg.get("activas") or list(REDES)
    maximo = int(cfg.get("max_resultados", 30))
    registros: list[dict] = []
    urls_vistas: set[str] = set()
    titulos_vistos: set[str] = set()

    for red in activas:
        if red not in REDES:
            continue
        query = _query(config, red, lookback_horas)
        if not query:
            continue
        log(f"Redes {REDES[red]['nombre']}: {query[:120]}")
        try:
            resp = requests.get(
                URL,
                params={
                    "q": query,
                    "hl": "es-419",
                    "gl": "CL",
                    "ceid": "CL:es-419",
                },
                headers={"User-Agent": UA},
                timeout=TIMEOUT,
            )
            resp.raise_for_status()
            feed = feedparser.parse(resp.content)
        except requests.RequestException as exc:
            log(f"  fallo al consultar {REDES[red]['nombre']}: {exc}")
            continue

        nuevos = 0
        for entry in feed.entries:
            fuente_feed = _fuente_feed(entry).strip().lower()
            titulo_sin_sufijo = _limpiar_red(str(entry.get("title") or ""), red)
            es_de_la_red = fuente_feed in REDES[red]["fuentes"] or _limpiar_red(
                str(entry.get("title") or ""), red
            ) != str(entry.get("title") or "")
            if not es_de_la_red:
                continue

            url = str(entry.get("link") or "")
            titulo = limpiar_titulo(titulo_sin_sufijo)
            clave_titulo = normalizar(titulo)
            if not titulo or (url and url in urls_vistas) or (clave_titulo and clave_titulo in titulos_vistos):
                continue

            href = entry.get("source")
            dominio_fuente = dominios.dominio(
                (href.get("href") if isinstance(href, dict) else "") or url
            )

            urls_vistas.add(url)
            titulos_vistos.add(clave_titulo)
            registros.append(
                {
                    "titulo": titulo,
                    "descripcion": limpiar_html(str(entry.get("summary") or "")),
                    "url": url,
                    "fuente": REDES[red]["nombre"],
                    "origen": red,
                    "dominio": dominio_fuente,
                    "publicado": _fecha(entry),
                }
            )
            nuevos += 1
            if nuevos >= maximo:
                break
        log(f"  {nuevos} publicaciones")

    # Misma regla de dominios que la busqueda web (.cl/.com).
    antes = len(registros)
    registros = dominios.filtrar(registros, config)
    if antes != len(registros):
        log(f"  descartados por dominio: {antes - len(registros)}")

    log(f"Total registros de redes: {len(registros)}")
    return registros
