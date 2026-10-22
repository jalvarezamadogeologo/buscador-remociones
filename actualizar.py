"""Orquestador del catastro: busca, clasifica, deduplica, geocodifica, guarda,
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

from buscar import buscar
from clasificar import clasificar
from comun import a_iso, ahora, cargar_config, log
from deduplicar import clave_registro, cargar_vistos, es_duplicado, guardar_vistos
from generar_sitio import generar_sitio
from geocodificar import geocodificar_eventos
from guardar import cargar_eventos, fusionar, guardar_eventos
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

    # 2) Deduplicacion persistente + duplicados entre medios
    vistos = cargar_vistos()
    existentes = cargar_eventos()
    dedup_cfg = config.get("deduplicacion") or {}
    umbral = float(dedup_cfg.get("umbral", 0.62))
    umbral_evento = float(dedup_cfg.get("umbral_mismo_evento", 0.20))
    umbral_sin_lugar = float(dedup_cfg.get("umbral_sin_lugar", 0.35))
    dias = int(dedup_cfg.get("dias", 4))
    deteccion = a_iso(ahora())
    nuevos: list[dict] = []
    claves_nuevas: dict[str, dict] = {}
    duplicados = 0
    for reg in clasificados:
        clave = clave_registro(reg)
        if clave in vistos or clave in claves_nuevas:
            continue
        reg["fecha_publicacion"] = a_iso(reg.get("publicado"))
        if es_duplicado(
            reg,
            existentes + nuevos,
            umbral=umbral,
            dias=dias,
            umbral_evento=umbral_evento,
            umbral_sin_lugar=umbral_sin_lugar,
        ):
            duplicados += 1
            claves_nuevas[clave] = {
                "titulo": reg.get("titulo", ""),
                "url": reg.get("url", ""),
                "fecha": deteccion,
                "duplicado": True,
            }
            continue
        claves_nuevas[clave] = {
            "titulo": reg.get("titulo", ""),
            "url": reg.get("url", ""),
            "fecha": deteccion,
        }
        evento = dict(reg)
        evento.pop("publicado", None)
        evento.update(
            {
                "id": clave,
                "fecha_deteccion": deteccion,
                "lat": "",
                "lon": "",
                "estado": "nuevo",
                "issue": "",
            }
        )
        nuevos.append(evento)
    log(f"eventos nuevos (no vistos): {len(nuevos)} | duplicados entre medios: {duplicados}")

    # 3) Fusion con el catastro existente
    eventos = fusionar(existentes, nuevos)

    # 4) Geocodificacion (incluye pendientes de corridas anteriores)
    geocodificados = 0
    if not args.sin_geocodificar:
        geocodificados = geocodificar_eventos(eventos, config, args.max_geocodificaciones)
        log(f"geocodificados en esta corrida: {geocodificados}")

    # 5) Persistencia
    guardar_eventos(eventos)
    vistos.update(claves_nuevas)
    guardar_vistos(vistos, actualizado=deteccion)

    # 6) Sitio estatico
    if not args.sin_sitio:
        destino = generar_sitio(eventos, config)
        log(f"sitio generado: {destino}")

    # 7) Notificacion por issues
    creados = 0
    if not args.sin_notificar:
        # Solo se notifican los eventos detectados en esta corrida; el catastro
        # historico no genera issues retroactivos.
        creados = notificar(eventos, config, solo_ids={e["id"] for e in nuevos})
        if creados:
            guardar_eventos(eventos)

    transcurrido = time.time() - inicio
    log(
        f"fin | nuevos {len(nuevos)} | duplicados {duplicados} | geocodificados {geocodificados} | "
        f"issues {creados} | total catastro {len(eventos)} | {transcurrido:.1f} s"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
