"""Orquestador del catastro: busca, clasifica, agrupa, geocodifica, guarda,
genera el sitio y notifica.

Uso:
    python actualizar.py                       # ultimas 24 h (config)
    python actualizar.py --lookback 72         # ultimas 72 h
    python actualizar.py --dias 7              # ultimos 7 dias
    python actualizar.py --sin-notificar       # no crea issues
    python actualizar.py --fuentes google_news # solo una fuente
"""

from __future__ import annotations

import argparse
import time
from typing import Sequence

from agrupar import agregar_fuente, buscar_evento, crear_evento
from buscar import buscar
from clasificar import clasificar
from comun import a_iso, ahora, cargar_config, log
from deduplicar import clave_registro, cargar_vistos, guardar_vistos
from generar_sitio import generar_sitio
from geocodificar import geocodificar_eventos
from guardar import cargar_eventos, guardar_eventos
from notificar import notificar


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Catastro de remociones en masa (Chile)")
    parser.add_argument("--config", default=None, help="ruta a config.yaml")
    parser.add_argument("--lookback", type=int, default=None, help="horas hacia atras")
    parser.add_argument("--dias", type=float, default=None, help="dias hacia atras (alternativa a --lookback)")
    parser.add_argument("--fuentes", default=None, help="fuentes separadas por coma (google_news,bing_news,nombre_feed)")
    parser.add_argument("--sin-geocodificar", action="store_true", help="no consultar Nominatim")
    parser.add_argument("--sin-sitio", action="store_true", help="no regenerar docs/index.html")
    parser.add_argument("--sin-notificar", action="store_true", help="no crear issues")
    parser.add_argument("--max-geocodificaciones", type=int, default=None, help="limite de geocodificaciones en esta corrida")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    inicio = time.time()
    config = cargar_config(args.config)

    if args.lookback:
        lookback = args.lookback
    elif args.dias:
        lookback = max(1, int(args.dias * 24))
    else:
        lookback = int(config.get("lookback_horas", 24))

    fuentes = [f.strip() for f in args.fuentes.split(",")] if args.fuentes else None
    log(f"inicio | ventana {lookback} h | fuentes: {', '.join(fuentes) if fuentes else 'todas'}")

    # 1) Busqueda y clasificacion
    registros = buscar(config, lookback_horas=lookback, activas=fuentes)
    clasificados = [c for r in registros if (c := clasificar(r, config))]
    log(f"clasificados como remocion en Chile: {len(clasificados)}")

    # 2) Agrupacion en eventos (tipo + lugar + fecha) con hasta 3 fuentes
    vistos = cargar_vistos()
    eventos = cargar_eventos()
    deteccion = a_iso(ahora())
    claves_nuevas: dict[str, dict] = {}
    ids_nuevos: set[str] = set()
    eventos_nuevos = 0
    fuentes_nuevas = 0
    for reg in clasificados:
        clave = clave_registro(reg)
        if clave in vistos or clave in claves_nuevas:
            continue
        claves_nuevas[clave] = {
            "titulo": reg.get("titulo", ""),
            "url": reg.get("url", ""),
            "fecha": deteccion,
        }
        evento = buscar_evento(eventos, reg)
        if evento is None:
            evento = crear_evento(reg, deteccion, clave)
            eventos.append(evento)
            ids_nuevos.add(evento["id"])
            eventos_nuevos += 1
            fuentes_nuevas += 1
        elif agregar_fuente(evento, reg):
            fuentes_nuevas += 1
    log(f"eventos nuevos: {eventos_nuevos} | fuentes agregadas: {fuentes_nuevas}")

    # 3) Geocodificacion (incluye pendientes de corridas anteriores)
    geocodificados = 0
    if not args.sin_geocodificar:
        geocodificados = geocodificar_eventos(eventos, config, args.max_geocodificaciones)
        log(f"geocodificados en esta corrida: {geocodificados}")

    # 4) Persistencia (vistos solo si hay claves nuevas)
    guardar_eventos(eventos)
    if claves_nuevas:
        vistos.update(claves_nuevas)
        guardar_vistos(vistos, actualizado=deteccion)

    # 5) Sitio estatico
    if not args.sin_sitio:
        destino = generar_sitio(eventos, config)
        log(f"sitio generado: {destino}")

    # 6) Notificacion por issues (solo eventos creados en esta corrida)
    creados = 0
    if not args.sin_notificar:
        creados = notificar(eventos, config, solo_ids=ids_nuevos)
        if creados:
            guardar_eventos(eventos)

    transcurrido = time.time() - inicio
    log(
        f"fin | eventos nuevos {eventos_nuevos} | fuentes {fuentes_nuevas} | "
        f"geocodificados {geocodificados} | issues {creados} | "
        f"total eventos {len(eventos)} | {transcurrido:.1f} s"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
