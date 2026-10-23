"""Barrido historico del catastro de remociones en masa.

Google News RSS entrega como maximo 100 entradas por consulta, asi que
`when:Nd` se satura y `--dias 90` y `--dias 120` devuelven lo mismo. Este
script recorre la ventana dia por dia con `after:`/`before:` (que si respetan
el rango) y alimenta el mismo pipeline que `actualizar.py`: clasificar, agrupar,
geocodificar, resolver enlaces y regenerar el sitio.

Uso:
    python historico.py --dias 120            # ultimos 120 dias, dia por dia
    python historico.py --dias 120 --dry-run  # solo informa, no escribe nada
    python historico.py --desde 2026-07-01 --hasta 2026-07-31
    python historico.py --dias 30 --sin-geocodificar --sin-sitio

No crea issues salvo que se pase --notificar. No corre en el workflow.
"""

from __future__ import annotations

import argparse
import time
from datetime import date, timedelta
from typing import Sequence

from agrupar import agregar_fuente, buscar_evento, crear_evento
from buscar import buscar_rango
from clasificar import clasificar
from comun import a_iso, ahora, cargar_config, log
from deduplicar import clave_registro, cargar_vistos, guardar_vistos
from generar_sitio import generar_sitio
from geocodificar import geocodificar_eventos
from guardar import cargar_eventos, guardar_eventos
from notificar import notificar
from resolver_url import resolver_eventos

MAX_SATURADO = 100


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Barrido historico del catastro")
    parser.add_argument("--config", default=None, help="ruta a config.yaml")
    parser.add_argument("--dias", type=int, default=120, help="dias hacia atras (default 120)")
    parser.add_argument("--desde", default=None, help="fecha inicial YYYY-MM-DD (alternativa a --dias)")
    parser.add_argument("--hasta", default=None, help="fecha final YYYY-MM-DD inclusiva (default hoy)")
    parser.add_argument("--pausa", type=float, default=1.2, help="segundos entre dias (default 1.2)")
    parser.add_argument("--max-resolver", type=int, default=100, help="enlaces a resolver (default 100)")
    parser.add_argument("--max-geocodificaciones", type=int, default=100, help="geocodificaciones (default 100)")
    parser.add_argument("--dry-run", action="store_true", help="no escribe nada, solo informa")
    parser.add_argument("--sin-geocodificar", action="store_true", help="no consultar Nominatim")
    parser.add_argument("--sin-sitio", action="store_true", help="no regenerar docs/index.html")
    parser.add_argument("--sin-resolver", action="store_true", help="no resolver enlaces de Google News")
    parser.add_argument("--notificar", action="store_true", help="crear issues por los eventos nuevos")
    return parser.parse_args(argv)


def rango_dias(inicio: date, fin: date) -> list[tuple[date, date]]:
    """Tramos [dia, dia+1) desde `inicio` hasta `fin` inclusive."""
    tramos = []
    dia = inicio
    while dia <= fin:
        tramos.append((dia, dia + timedelta(days=1)))
        dia += timedelta(days=1)
    return tramos


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    inicio_reloj = time.time()
    config = cargar_config(args.config)

    hasta = date.fromisoformat(args.hasta) if args.hasta else ahora().date()
    if args.desde:
        desde = date.fromisoformat(args.desde)
    else:
        desde = hasta - timedelta(days=max(1, args.dias))
    if desde > hasta:
        log(f"ERROR: --desde {desde} es posterior a --hasta {hasta}")
        return 2

    tramos = rango_dias(desde, hasta)
    log(f"barrido historico | {desde} .. {hasta} | {len(tramos)} dias | pausa {args.pausa}s")
    if args.dry_run:
        log("modo dry-run: no se escriben datos, sitio ni vistos")

    vistos = cargar_vistos()
    eventos = cargar_eventos()
    eventos_iniciales = len(eventos)
    deteccion = a_iso(ahora())
    claves_nuevas: dict[str, dict] = {}
    ids_nuevos: set[str] = set()
    eventos_nuevos = 0
    fuentes_nuevas = 0
    registros_total = 0
    clasificados_total = 0
    dias_saturados: list[str] = []

    for desde_dia, hasta_dia in tramos:
        registros = buscar_rango(config, desde_dia, hasta_dia)
        if len(registros) >= MAX_SATURADO:
            dias_saturados.append(desde_dia.isoformat())
        registros_total += len(registros)
        clasificados = [c for r in registros if (c := clasificar(r, config))]
        clasificados_total += len(clasificados)
        nuevos_dia = 0
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
                nuevos_dia += 1
            elif agregar_fuente(evento, reg):
                fuentes_nuevas += 1
        log(f"{desde_dia}: {len(registros)} registros | {len(clasificados)} clasificados | {nuevos_dia} eventos nuevos")
        if args.pausa and (desde_dia, hasta_dia) != tramos[-1]:
            time.sleep(args.pausa)

    log(
        f"barrido terminado | registros {registros_total} | clasificados {clasificados_total} | "
        f"eventos nuevos {eventos_nuevos} | fuentes {fuentes_nuevas}"
    )
    if dias_saturados:
        log(
            f"AVISO: {len(dias_saturados)} dias llegaron al tope de {MAX_SATURADO} entradas "
            f"({', '.join(dias_saturados[:5])}{'...' if len(dias_saturados) > 5 else ''}): "
            "puede faltar cobertura en esos dias"
        )

    if args.dry_run:
        log(f"dry-run: total de eventos en el catalogo seguiria en {eventos_iniciales}")
        return 0

    geocodificados = 0
    if not args.sin_geocodificar:
        geocodificados = geocodificar_eventos(eventos, config, args.max_geocodificaciones)
        log(f"geocodificados: {geocodificados}")

    if not args.sin_resolver:
        cfg_enlaces = config.get("resolver_urls") or {}
        if cfg_enlaces.get("activo", True):
            enlaces = resolver_eventos(
                eventos,
                maximo=args.max_resolver,
                pausa=float(cfg_enlaces.get("pausa", 0.4)),
                timeout=int(cfg_enlaces.get("timeout", 15)),
            )
            log(
                f"enlaces resueltos: {enlaces['resueltos']} (cache {enlaces['cacheados']}, "
                f"fallidos {enlaces['fallidos']}, omitidos {enlaces['omitidos']})"
            )

    guardar_eventos(eventos)
    if claves_nuevas:
        vistos.update(claves_nuevas)
        guardar_vistos(vistos, actualizado=deteccion)

    if not args.sin_sitio:
        destino = generar_sitio(eventos, config)
        log(f"sitio generado: {destino}")

    creados = 0
    if args.notificar:
        creados = notificar(eventos, config, solo_ids=ids_nuevos)
        if creados:
            guardar_eventos(eventos)

    transcurrido = time.time() - inicio_reloj
    log(
        f"fin | eventos nuevos {eventos_nuevos} | geocodificados {geocodificados} | "
        f"issues {creados} | total eventos {len(eventos)} | {transcurrido:.1f} s"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
