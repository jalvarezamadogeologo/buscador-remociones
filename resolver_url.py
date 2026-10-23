"""Resuelve enlaces de Google News RSS a la URL original del medio.

Google News entrega enlaces del tipo `news.google.com/rss/articles/<ID>?oc=5`.
Ese enlace, abierto en el navegador, responde con "We're sorry... your computer
or network may be sending automated queries", asi que no sirve para el operador.
El id es opaco; la URL real se obtiene con el RPC interno `Fbv4je` de Google
(batchexecute), usando la firma y el timestamp que la propia pagina del articulo
publica en `data-n-a-sg` / `data-n-a-ts`.

Sin API keys. Si el endpoint cambia, `resolver()` devuelve None y se conserva el
enlace original de Google News. Los resultados (incluidos los fallos) se cachean
en `data/urlcache.json` para no repetir peticiones en cada corrida.
"""

from __future__ import annotations

import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

from comun import DATA, escribir_json, leer_json

CACHE = DATA / "urlcache.json"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36"
)
CABECERAS = {"User-Agent": USER_AGENT, "Accept-Language": "es-CL,es;q=0.9"}
URL_RPC = "https://news.google.com/_/DotsSplashUi/data/batchexecute"

_PATRON_ID = re.compile(r"news\.google\.com/(?:rss/)?articles/([^?/#]+)")
_PATRON_TS = re.compile(r'data-n-a-ts="([^"]+)"')
_PATRON_SG = re.compile(r'data-n-a-sg="([^"]+)"')
_PATRON_DESTINO = re.compile(r'\\"garturl(?:res|ok)\\",\\"(.*?)\\"')


def es_enlace_google_news(url: str | None) -> bool:
    """True si la URL es un enlace de articulo de Google News."""
    return bool(url) and "news.google.com/" in url and "/articles/" in url


def id_articulo(url: str) -> str | None:
    """Extrae el id opaco del enlace de Google News."""
    coincidencia = _PATRON_ID.search(url or "")
    return coincidencia.group(1) if coincidencia else None


def extraer_parametros(html: str) -> dict[str, str] | None:
    """Lee la firma y el timestamp que Google publica en la pagina del articulo."""
    ts = _PATRON_TS.search(html)
    sg = _PATRON_SG.search(html)
    if not (ts and sg):
        return None
    return {"ts": ts.group(1), "sg": sg.group(1)}


def construir_cuerpo(articulo_id: str, ts: str, sg: str) -> str:
    """Arma el cuerpo `f.req` del RPC Fbv4je (batchexecute)."""
    interno = (
        '["garturlreq",[["X","X",["X","X"],null,null,1,1,"US:en",null,1,null,null,null,'
        'null,null,0,1],"X","X",1,[1,1,1],1,1,null,0,0,null,0],'
        f'"{articulo_id}",{int(ts)},"{sg}"]'
    )
    carga = [[["Fbv4je", interno, None, "generic"]]]
    return "f.req=" + urllib.parse.quote(json.dumps(carga, separators=(",", ":")))


def parsear_destino(texto: str) -> str | None:
    """Extrae la URL del medio desde la respuesta del RPC."""
    coincidencia = _PATRON_DESTINO.search(texto or "")
    if not coincidencia:
        return None
    url = coincidencia.group(1)
    return url.replace("\\u003d", "=").replace("\\u0026", "&").replace("\\/", "/")


def _descargar(url: str, timeout: int = 15) -> str:
    peticion = urllib.request.Request(url, headers=CABECERAS)
    with urllib.request.urlopen(peticion, timeout=timeout) as respuesta:
        return respuesta.read().decode("utf-8", "replace")


def _batchexecute(cuerpo: str, timeout: int = 15) -> str:
    peticion = urllib.request.Request(
        URL_RPC,
        data=cuerpo.encode("utf-8"),
        headers={**CABECERAS, "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8"},
    )
    with urllib.request.urlopen(peticion, timeout=timeout) as respuesta:
        return respuesta.read().decode("utf-8", "replace")


def resolver(url: str, timeout: int = 15) -> str | None:
    """Devuelve la URL original del medio, o None si no se puede resolver."""
    articulo = id_articulo(url)
    if not articulo:
        return None
    parametros = extraer_parametros(_descargar(url, timeout))
    if not parametros:
        return None
    texto = _batchexecute(construir_cuerpo(articulo, parametros["ts"], parametros["sg"]), timeout)
    destino = parsear_destino(texto)
    if not destino or es_enlace_google_news(destino):
        return None
    return destino


def cargar_cache(ruta: Path = CACHE) -> dict[str, str]:
    datos = leer_json(ruta, {})
    return datos if isinstance(datos, dict) else {}


def guardar_cache(cache: dict[str, str], ruta: Path = CACHE) -> None:
    escribir_json(ruta, cache)


def resolver_eventos(
    eventos: list[dict],
    maximo: int = 30,
    pausa: float = 0.4,
    timeout: int = 15,
    cache_path: Path = CACHE,
    reintentar_fallidos: bool = False,
) -> dict[str, int]:
    """Reemplaza en los eventos las URLs de Google News por la del medio.

    Devuelve contadores: resueltos, cacheados, fallidos, intentados y omitidos.
    `maximo` limita las peticiones de red de esta corrida (los fallos se cachean
    y no se reintentan salvo con `reintentar_fallidos`).
    """
    cache = cargar_cache(cache_path)
    stats = {"resueltos": 0, "cacheados": 0, "fallidos": 0, "intentados": 0, "omitidos": 0}
    cambios = False

    for evento in eventos:
        for indice in (1, 2, 3):
            url = evento.get(f"url_{indice}") or ""
            if not es_enlace_google_news(url):
                continue
            if url in cache and cache[url]:
                evento[f"url_{indice}"] = cache[url]
                stats["cacheados"] += 1
                continue
            if url in cache and not cache[url] and not reintentar_fallidos:
                continue
            if stats["intentados"] >= maximo:
                stats["omitidos"] += 1
                continue

            if stats["intentados"] and pausa:
                time.sleep(pausa)
            stats["intentados"] += 1
            try:
                destino = resolver(url, timeout=timeout)
            except Exception:  # red caida: no cortar el pipeline por un enlace
                destino = None
            cache[url] = destino or ""
            cambios = True
            if destino:
                evento[f"url_{indice}"] = destino
                stats["resueltos"] += 1
            else:
                stats["fallidos"] += 1

    if cambios:
        guardar_cache(cache, cache_path)
    return stats
