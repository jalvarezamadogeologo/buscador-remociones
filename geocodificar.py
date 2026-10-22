"""Geocodificacion de eventos con Nominatim (sin API key) + cache + overrides manuales.

El archivo data/georref.json permite fijar coordenadas a mano (ganan sobre
Nominatim). Formato:

    {"claves": {"La Ligua": {"lat": -32.45, "lon": -71.23}}}
"""

from __future__ import annotations

import time
from pathlib import Path

import requests

from comun import DATA, leer_json, log, normalizar

GEOCACHE = DATA / "geocache.json"
GEORREF = DATA / "georref.json"
URL = "https://nominatim.openstreetmap.org/search"
UA = "catastro-remociones/1.0 (+https://github.com/jalvarezamadogeologo/catastro-remociones)"
PAUSA = 1.1  # politica de uso de Nominatim: max 1 req/s


def cargar_manual(ruta: Path = GEORREF) -> dict:
    datos = leer_json(ruta, {})
    if isinstance(datos, dict) and "claves" in datos:
        return datos["claves"]
    return datos if isinstance(datos, dict) else {}


def _buscar_manual(manual: dict, candidatos: list[str]) -> tuple[float, float] | None:
    indice = {normalizar(k): v for k, v in manual.items()}
    for cand in candidatos:
        valor = indice.get(normalizar(cand))
        if isinstance(valor, dict) and valor.get("lat") is not None:
            return float(valor["lat"]), float(valor["lon"])
    return None


def _nominatim(consulta: str) -> tuple[float, float] | None:
    try:
        resp = requests.get(
            URL,
            params={
                "q": consulta,
                "format": "json",
                "limit": 1,
                "countrycodes": "cl",
                "addressdetails": 0,
            },
            headers={"User-Agent": UA},
            timeout=20,
        )
        resp.raise_for_status()
        datos = resp.json()
        if datos:
            return float(datos[0]["lat"]), float(datos[0]["lon"])
    except (requests.RequestException, ValueError, KeyError) as exc:
        log(f"  Nominatim fallo para '{consulta}': {exc}")
    return None


def geocodificar_eventos(eventos: list[dict], config: dict, maximo: int | None = None) -> int:
    """Completa lat/lon de eventos sin coordenadas. Devuelve cuantos geocodifico."""
    manual = cargar_manual()
    cache = leer_json(GEOCACHE, {})
    if not isinstance(cache, dict):
        cache = {}
    maximo = int((config or {}).get("max_geocodificaciones", 15)) if maximo is None else maximo
    hechos = 0

    for evento in eventos:
        if hechos >= maximo:
            break
        if evento.get("estado") == "descartado":
            continue
        if evento.get("lat") and evento.get("lon"):
            continue

        candidatos = [c for c in (evento.get("comuna"), evento.get("region")) if c]
        if not candidatos:
            continue
        consulta = f"{candidatos[0]}, Chile"

        coords = _buscar_manual(manual, candidatos + [consulta])
        origen = "manual"
        if coords is None:
            clave_cache = normalizar(consulta)
            if clave_cache in cache:
                valor = cache[clave_cache]
                coords = (valor["lat"], valor["lon"]) if valor else None
                origen = "cache"
            else:
                log(f"  geocodificando: {consulta}")
                time.sleep(PAUSA)
                par = _nominatim(consulta)
                cache[clave_cache] = {"lat": par[0], "lon": par[1]} if par else None
                coords = par
                origen = "nominatim"

        if coords:
            evento["lat"] = f"{coords[0]:.6f}"
            evento["lon"] = f"{coords[1]:.6f}"
            hechos += 1
            log(f"  {consulta} -> {evento['lat']}, {evento['lon']} ({origen})")

    from comun import escribir_json

    escribir_json(GEOCACHE, cache)
    return hechos
