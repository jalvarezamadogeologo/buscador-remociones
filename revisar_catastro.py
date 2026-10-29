"""Revisa el catastro existente y aplica las correcciones de calidad.

- Descarta (estado=descartado) notas de prevencion/contexto que no son eventos.
- Quita las fuentes de dominios no permitidos (solo .cl y .com) y los eventos
  que se quedan sin ninguna fuente.
- Corrige fuentes guardadas como URL en vez del nombre del medio.
- Re-geocodifica los eventos cuyo titulo nombra un toponimo conocido
  (`geografia.toponimos`), aunque ya tuvieran coordenadas del centro de la comuna.
- Regenera el sitio.

Uso:
    python revisar_catastro.py
    python revisar_catastro.py --sin-geocodificar
    python revisar_catastro.py --sin-sitio
"""

from __future__ import annotations

import argparse
from typing import Sequence

import dominios
from buscar import nombre_medio
from clasificar import es_prevencion
from comun import cargar_config, log, normalizar
from generar_sitio import generar_sitio
from geocodificar import geocodificar_eventos
from guardar import cargar_eventos, guardar_eventos


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Revisar y corregir el catastro existente")
    parser.add_argument("--config", default=None, help="ruta a config.yaml")
    parser.add_argument("--sin-geocodificar", action="store_true", help="no recalcular toponimos")
    parser.add_argument("--sin-sitio", action="store_true", help="no regenerar docs/index.html")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    config = cargar_config(args.config)
    eventos = cargar_eventos()
    log(f"eventos en el catastro: {len(eventos)}")

    descartados = 0
    for evento in eventos:
        if evento.get("estado") == "descartado":
            continue
        if es_prevencion(normalizar(evento.get("titulo", "")), config):
            evento["estado"] = "descartado"
            descartados += 1
            log(f"  descartado (prevencion/contexto): {evento.get('titulo', '')[:80]}")
    log(f"descartados por prevencion/contexto: {descartados}")

    corregidas = 0
    for evento in eventos:
        for indice in (1, 2, 3):
            medio = evento.get(f"fuente_{indice}") or ""
            if "://" in medio:
                nuevo = nombre_medio(medio)
                log(f"  fuente {indice} de {evento.get('id')}: '{medio}' -> '{nuevo}'")
                evento[f"fuente_{indice}"] = nuevo
                corregidas += 1
    log(f"fuentes con URL corregidas: {corregidas}")

    ids_antes = [evento.get("id") for evento in eventos]
    purga = dominios.purgar_eventos(eventos, config)
    eventos = purga["eventos"]
    ids_despues = {evento.get("id") for evento in eventos}
    eliminados = [i for i in ids_antes if i not in ids_despues]
    log(
        f"fuentes de dominios no permitidos: {purga['fuentes_quitadas']} | "
        f"eventos sin fuente .cl/.com eliminados: {purga['eventos_quitados']}"
    )
    for identificador in eliminados:
        log(f"  eliminado: {identificador}")

    geocodificados = 0
    if not args.sin_geocodificar:
        geocodificados = geocodificar_eventos(eventos, config, maximo=50, forzar=True)
        log(f"re-geocodificados por toponimo: {geocodificados}")

    guardar_eventos(eventos)
    if not args.sin_sitio:
        log(f"sitio generado: {generar_sitio(eventos, config)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
