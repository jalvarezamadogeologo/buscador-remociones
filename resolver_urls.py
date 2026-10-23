"""Resuelve los enlaces de Google News del catastro existente a la URL del medio.

Recorre `data/eventos.csv`, reemplaza las URLs de Google News (`url_1..3`) por la
URL original del medio y regenera el sitio. Usa cache, asi que se puede correr
varias veces sin repetir peticiones.

Uso:
    python resolver_urls.py
    python resolver_urls.py --maximo 100 --pausa 0.3
    python resolver_urls.py --reintentar-fallidos
    python resolver_urls.py --sin-sitio
"""

from __future__ import annotations

import argparse
from typing import Sequence

from comun import cargar_config, log
from generar_sitio import generar_sitio
from guardar import cargar_eventos, guardar_eventos
from resolver_url import CACHE, resolver_eventos


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Resolver enlaces de Google News del catastro")
    parser.add_argument("--config", default=None, help="ruta a config.yaml")
    parser.add_argument("--maximo", type=int, default=200, help="maximo de peticiones en esta corrida")
    parser.add_argument("--pausa", type=float, default=0.4, help="segundos entre peticiones")
    parser.add_argument("--timeout", type=int, default=15, help="timeout por peticion")
    parser.add_argument("--reintentar-fallidos", action="store_true", help="reintentar URLs que fallaron antes")
    parser.add_argument("--sin-sitio", action="store_true", help="no regenerar docs/index.html")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    eventos = cargar_eventos()
    log(f"eventos en el catastro: {len(eventos)} | cache: {CACHE}")

    stats = resolver_eventos(
        eventos,
        maximo=args.maximo,
        pausa=args.pausa,
        timeout=args.timeout,
        reintentar_fallidos=args.reintentar_fallidos,
    )
    log(
        f"enlaces: resueltos {stats['resueltos']} | cacheados {stats['cacheados']} | "
        f"fallidos {stats['fallidos']} | intentados {stats['intentados']} | omitidos {stats['omitidos']}"
    )

    guardar_eventos(eventos)
    if not args.sin_sitio:
        log(f"sitio generado: {generar_sitio(eventos, cargar_config(args.config))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
