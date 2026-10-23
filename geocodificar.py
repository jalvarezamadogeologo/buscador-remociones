"""Geocodificacion de eventos con Nominatim (sin API key) + cache + overrides manuales.

El archivo data/georref.json permite fijar coordenadas a mano (ganan sobre
Nominatim). Formato:

    {"claves": {"La Ligua": {"lat": -32.45, "lon": -71.23}}}

Los `toponimos` de `geografia` en config.yaml (Portillo, Laguna del Inca,
Paso Cristo Redentor, El Japonés, Caracoles, ...) se buscan en el titulo del
evento antes que la comuna/region: son mas especificos y evitan geocodificar
el centro de la comuna cuando la noticia nombra un paraje o sector.
"""

from __future__ import annotations

import time
from pathlib import Path

import requests

from comun import DATA, contiene, leer_json, log, normalizar

GEOCACHE = DATA / "geocache.json"
GEORREF = DATA / "georref.json"
URL = "https://nominatim.openstreetmap.org/search"
UA = "buscador-remociones/1.0 (+https://github.com/jalvarezamadogeologo/buscador-remociones)"
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


def toponimos_detectados(evento: dict, config: dict) -> list[str]:
    """Toponimos de `geografia.toponimos` que aparecen en el titulo del evento.

    Se devuelven ordenados de mas largo a mas corto para preferir el nombre
    especifico ("Laguna del Inca" antes que "Inca").
    """
    texto = normalizar(evento.get("titulo", ""))
    if not texto:
        return []
    claves = (config.get("geografia") or {}).get("toponimos") or []
    hallados = [c for c in claves if contiene(texto, c)]
    return sorted(set(hallados), key=len, reverse=True)


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


def geocodificar_eventos(
    eventos: list[dict], config: dict, maximo: int | None = None, forzar: bool = False
) -> int:
    """Completa lat/lon de eventos sin coordenadas. Devuelve cuantos geocodifico.

    Con `forzar=True` recalcula solo los eventos cuyo titulo nombra un toponimo
    conocido (util para corregir eventos ya geocodificados con el centro de la
    comuna/region).
    """
    manual = cargar_manual()
    cache = leer_json(GEOCACHE, {})
    if not isinstance(cache, dict):
        cache = {}
    if maximo is None:
        maximo = int((config or {}).get("max_geocodificaciones", 15))
    hechos = 0

    for evento in eventos:
        if hechos >= maximo:
            break
        if evento.get("estado") == "descartado":
            continue

        especificos = toponimos_detectados(evento, config)
        if forzar and not especificos:
            continue
        if not forzar and evento.get("lat") and evento.get("lon"):
            continue

        candidatos = especificos + [c for c in (evento.get("comuna"), evento.get("region")) if c]
        if not candidatos:
            continue

        # Consultas de mas a menos especifica: "toponimo, comuna, Chile" evita
        # homonimos (p. ej. Caracoles de Malloa vs Caracoles de Los Andes).
        comuna = evento.get("comuna") or ""
        region = evento.get("region") or ""
        consultas: list[str] = []
        for toponimo in especificos:
            if comuna:
                consultas.append(f"{toponimo}, {comuna}, Chile")
            if region:
                consultas.append(f"{toponimo}, {region}, Chile")
            consultas.append(f"{toponimo}, Chile")
        for lugar in (comuna, region):
            if lugar:
                consultas.append(f"{lugar}, Chile")
        consultas = list(dict.fromkeys(consultas))

        coords = _buscar_manual(manual, especificos + [comuna, region] + consultas)
        origen = "manual"
        consulta = ""
        if coords is None:
            for consulta in consultas:
                clave_cache = normalizar(consulta)
                if clave_cache in cache:
                    valor = cache[clave_cache]
                    coords = (valor["lat"], valor["lon"]) if valor else None
                    origen = "cache"
                    if coords is not None:
                        break
                    continue
                log(f"  geocodificando: {consulta}")
                time.sleep(PAUSA)
                par = _nominatim(consulta)
                cache[clave_cache] = {"lat": par[0], "lon": par[1]} if par else None
                coords = par
                origen = "nominatim"
                if coords is not None:
                    break

        if coords:
            evento["lat"] = f"{coords[0]:.6f}"
            evento["lon"] = f"{coords[1]:.6f}"
            hechos += 1
            etiqueta = consulta or (especificos[0] if especificos else comuna or region)
            log(f"  {etiqueta} -> {evento['lat']}, {evento['lon']} ({origen})")

    from comun import escribir_json

    escribir_json(GEOCACHE, cache)
    return hechos
