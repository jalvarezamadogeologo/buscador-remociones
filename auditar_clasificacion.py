"""Audita la clasificacion del catalogo y lista lo que conviene revisar.

Muestra dos grupos:

- **descartar**: eventos publicados que la regla del objeto del hecho daria de
  baja (colapso de una estructura, metafora, mencion hipotetica). Se corrigen
  con `python revisar_catastro.py`.
- **revisar**: eventos ya marcados con `confianza = baja` (derrumbe de una
  vivienda sin evidencia de terreno, agente no geologico) esperando la
  decision del operador.

Uso:
    python auditar_clasificacion.py
    python auditar_clasificacion.py --solo-revisar
"""

from __future__ import annotations

import argparse
from typing import Sequence

from clasificar import agente_no_geologico, es_hipotetico, evaluar_objeto
from comun import log, normalizar
from guardar import cargar_eventos


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Auditar la clasificacion del catalogo")
    parser.add_argument("--solo-revisar", action="store_true", help="no listar los descartables")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    eventos = [e for e in cargar_eventos() if e.get("estado") != "descartado"]
    log(f"eventos publicados: {len(eventos)}")

    descartables: list[tuple[dict, str]] = []
    pendientes: list[dict] = []
    for evento in eventos:
        titulo_n = normalizar(evento.get("titulo", ""))
        if evento.get("confianza") == "baja":
            pendientes.append(evento)
        if args.solo_revisar or evento.get("estado") == "confirmado":
            continue
        veredicto, motivo_objeto = evaluar_objeto(titulo_n)
        if es_hipotetico(titulo_n) or veredicto == "descartar":
            descartables.append((evento, motivo_objeto or "mencion hipotetica del proceso"))
        elif agente_no_geologico(titulo_n) and evento.get("confianza") != "baja":
            descartables.append((evento, f"agente no geologico: {agente_no_geologico(titulo_n)}"))

    if not args.solo_revisar:
        log(f"candidatos a descartar: {len(descartables)}")
        for evento, motivo in descartables:
            print(f"  DESCARTAR {evento.get('tipo_evento', ''):<14} {evento.get('titulo', '')[:70]}")
            print(f"            {motivo}")

    log(f"marcados para revision: {len(pendientes)}")
    for evento in pendientes:
        print(f"  REVISAR   {evento.get('tipo_evento', ''):<14} {evento.get('titulo', '')[:70]}")
        print(f"            {evento.get('motivo', '')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
