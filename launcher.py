"""Punto de entrada del ejecutable portable.

Prepara la carpeta de datos junto al .exe (o en %LOCALAPPDATA% si no se puede
escribir), siembra el catalogo inicial la primera vez y levanta el servidor
local en un puerto libre, abriendo el navegador.

Uso empaquetado: doble clic en `buscador-remociones.exe`.
Uso en desarrollo: `python launcher.py`.
"""

from __future__ import annotations

import shutil
import sys

from comun import DATA, DOCS, RAIZ, RECURSOS, cargar_config, log
from guardar import guardar_eventos
import generar_sitio

# Archivos de datos que se copian la primera vez desde `semilla/`.
SEMILLA = (
    "eventos.csv",
    "eventos.json",
    "georref.json",
    "vistos.json",
    "urlcache.json",
    "geocache.json",
)


def preparar_entorno() -> None:
    """Crea data/ y docs/, copia config.yaml y la semilla si faltan."""
    DATA.mkdir(parents=True, exist_ok=True)
    DOCS.mkdir(parents=True, exist_ok=True)
    cargar_config()  # copia el config.yaml empaquetado si no existe junto a los datos

    for nombre in SEMILLA:
        destino = DATA / nombre
        origen = RECURSOS / "semilla" / nombre
        if not destino.exists() and origen.exists():
            shutil.copyfile(origen, destino)

    if not (DATA / "eventos.csv").exists():
        guardar_eventos([])  # catalogo vacio con cabecera

    if not (DOCS / "index.html").exists() or not (DOCS / "eventos.json").exists():
        generar_sitio.generar_sitio(config=cargar_config())


def main() -> int:
    preparar_entorno()
    log(f"datos en: {RAIZ}")
    from servidor import main as servidor_main

    # Sin argumentos usa un puerto libre; se aceptan los de servidor.py
    # (--puerto, --no-abrir, --lookback) para pruebas o uso manual.
    argv = sys.argv[1:] or ["--puerto", "0"]
    return servidor_main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
