"""Busqueda de noticias sobre remociones en masa en fuentes RSS publicas.

No requiere API keys: usa Google News RSS, Bing News RSS y, opcionalmente,
feeds RSS directos declarados en config.yaml.
"""

from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlencode, urlparse

import feedparser
import requests

from comun import limpiar_html, limpiar_titulo, log, normalizar

UA = (
    "buscador-remociones/1.0 "
    "(monitoreo de remociones en masa; +https://github.com/jalvarezamadogeologo/buscador-remociones)"
)
TIMEOUT = 30
REINTENTOS = 2


def _descargar(url: str) -> bytes | None:
    """Descarga una URL con timeout y reintentos simples."""
    for intento in range(1, REINTENTOS + 1):
        try:
            resp = requests.get(url, headers={"User-Agent": UA}, timeout=TIMEOUT)
            resp.raise_for_status()
            return resp.content
        except requests.RequestException as exc:
            log(f"fallo al descargar {url} (intento {intento}/{REINTENTOS}): {exc}")
            if intento < REINTENTOS:
                time.sleep(3)
    return None


def _fecha_de_entry(entry) -> datetime | None:
    """Convierte published_parsed (UTC) a datetime con tz."""
    struct = entry.get("published_parsed") or entry.get("updated_parsed")
    if not struct:
        return None
    try:
        return datetime(*struct[:6], tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None


def _url_real_bing(link: str) -> str:
    """Extrae la URL destino del redirect de Bing (parametro url=)."""
    try:
        valores = parse_qs(urlparse(link).query).get("url")
        if valores:
            return valores[0]
    except ValueError:
        pass
    return link


def nombre_medio(fuente: str, url_defecto: str = "") -> str:
    """Devuelve un nombre de medio legible.

    Algunos feeds traen la URL del medio en el campo `source` en vez del nombre
    (p. ej. "https://auroranoticias.cl/"). En ese caso se usa el dominio.
    """
    texto = limpiar_html(str(fuente or "")).strip()
    if texto and "://" not in texto and not texto.lower().startswith("www."):
        return texto
    candidata = texto if "://" in texto else (url_defecto or "")
    try:
        host = urlparse(candidata).netloc.lower()
    except ValueError:
        host = ""
    host = host[4:] if host.startswith("www.") else host
    return host or "Google News"


def _fuente_google(entry) -> str:
    src = entry.get("source")
    if isinstance(src, dict):
        return limpiar_html(str(src.get("title", ""))) or "Google News"
    return limpiar_html(str(src or "")) or "Google News"


def construir_query(config: dict, lookback_horas: int, con_ventana: bool) -> str:
    """Arma la consulta web con los terminos principales de los tipos de evento.

    Google News deja de respetar `when:Nd` si la consulta lleva comillas o
    demasiados terminos; por eso la busqueda usa solo palabras sueltas
    (las frases quedan para la clasificacion local).
    """
    terminos: list[str] = []
    for tipo in (config.get("tipos_evento") or {}).values():
        for clave in tipo.get("claves", []):
            if " " not in clave and clave not in terminos:
                terminos.append(clave)
    max_terminos = int((config.get("consulta") or {}).get("max_terminos", 8))
    terminos = terminos[:max_terminos]

    query = "(" + " OR ".join(terminos) + ")"

    if con_ventana and (config.get("consulta") or {}).get("sufijo_ventana", True):
        if lookback_horas <= 48:
            dias = max(1, lookback_horas // 24 or 1)
        else:
            dias = max(1, round(lookback_horas / 24))
        query += f" when:{dias}d"
    return query


def _registros_desde_feed(contenido: bytes, origen: str, fuente_defecto: str) -> list[dict]:
    """Parsea un feed y devuelve registros normalizados."""
    feed = feedparser.parse(contenido)
    registros = []
    for entry in feed.entries:
        titulo = limpiar_titulo(str(entry.get("title") or ""))
        if not titulo:
            continue
        link = str(entry.get("link") or "")
        if origen == "bing_news" and link:
            link = _url_real_bing(link)
        descripcion = limpiar_html(str(entry.get("summary") or entry.get("description") or ""))
        if origen == "google_news":
            fuente = nombre_medio(_fuente_google(entry), link)
        elif origen == "bing_news":
            fuente = nombre_medio(limpiar_html(str(entry.get("news_source") or "")) or fuente_defecto, link)
        else:
            fuente = fuente_defecto
        # Google/Bing a veces dejan " - Nombre del medio" al final del titulo.
        for sufijo in (f" - {fuente}", f" | {fuente}"):
            if fuente and titulo.endswith(sufijo):
                titulo = titulo[: -len(sufijo)].strip()
                break
        registros.append(
            {
                "titulo": titulo,
                "descripcion": descripcion,
                "url": link,
                "fuente": fuente,
                "origen": origen,
                "publicado": _fecha_de_entry(entry),
            }
        )
    return registros


def _dentro_de_ventana(registro: dict, lookback_horas: int) -> bool:
    """Descarta noticias publicadas fuera de la ventana (si hay fecha)."""
    publicado = registro.get("publicado")
    if not publicado:
        return True
    limite = datetime.now(timezone.utc) - timedelta(hours=lookback_horas)
    # Margen de 12 h: los agregadores publican con retraso y desfase de zona.
    return publicado >= limite - timedelta(hours=12)


def buscar(config: dict, lookback_horas: int = 24, activas: list[str] | None = None) -> list[dict]:
    """Consulta las fuentes activas y devuelve registros crudos deduplicados."""
    fuentes = config.get("fuentes") or {}
    activas = activas or []
    todos: list[dict] = []

    def _activa(nombre: str, default: bool = True) -> bool:
        return (fuentes.get(nombre) or {}).get("activa", default) and (not activas or nombre in activas)

    if _activa("google_news"):
        fdef = fuentes["google_news"]
        params = dict(fdef.get("parametros") or {})
        query = construir_query(config, lookback_horas, con_ventana=True)
        params["q"] = query
        url = f"{fdef['base']}?{urlencode(params)}"
        log(f"Google News: {query}")
        contenido = _descargar(url)
        if contenido:
            nuevos = _registros_desde_feed(contenido, "google_news", "Google News")
            log(f"  {len(nuevos)} entradas")
            todos.extend(nuevos)

    if _activa("bing_news"):
        fdef = fuentes["bing_news"]
        # Bing no soporta OR: una consulta por termino representativo de cada tipo.
        terminos = []
        for tipo in (config.get("tipos_evento") or {}).values():
            for clave in tipo.get("claves", []):
                if " " not in clave:
                    if clave not in terminos:
                        terminos.append(clave)
                    break
        log(f"Bing News: {len(terminos)} consultas ({', '.join(terminos)})")
        for termino in terminos:
            params = dict(fdef.get("parametros") or {})
            params["q"] = termino
            url = f"{fdef['base']}?{urlencode(params)}"
            contenido = _descargar(url)
            if contenido:
                todos.extend(_registros_desde_feed(contenido, "bing_news", "Bing News"))

    for feed_def in fuentes.get("feeds_rss") or []:
        nombre = feed_def.get("nombre") or feed_def.get("url", "RSS")
        if activas and nombre not in activas:
            continue
        log(f"RSS {nombre}")
        contenido = _descargar(str(feed_def.get("url", "")))
        if contenido:
            nuevos = _registros_desde_feed(contenido, nombre, nombre)
            nuevos = [r for r in nuevos if _dentro_de_ventana(r, lookback_horas)]
            log(f"  {len(nuevos)} entradas")
            todos.extend(nuevos)

    # Filtro temporal para todas las fuentes (los agregadores devuelven
    # resultados fuera de la ventana solicitada).
    todos = [r for r in todos if _dentro_de_ventana(r, lookback_horas)]

    # Deduplicacion basica dentro de la corrida (url o titulo normalizado).
    vistos_url: set[str] = set()
    vistos_titulo: set[str] = set()
    unicos: list[dict] = []
    for reg in todos:
        url = (reg.get("url") or "").strip()
        titulo = normalizar(reg.get("titulo"))
        if (url and url in vistos_url) or (titulo and titulo in vistos_titulo):
            continue
        if url:
            vistos_url.add(url)
        if titulo:
            vistos_titulo.add(titulo)
        unicos.append(reg)

    log(f"Total registros unicos: {len(unicos)}")
    return unicos
