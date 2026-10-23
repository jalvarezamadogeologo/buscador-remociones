"""Cambio del estado de revision de un evento.

Los estados viven en `data/eventos.csv` (columna `estado`) y los edita el
operador: `nuevo` (detectado, sin revisar), `confirmado` (verificado) y
`descartado` (falso positivo o fuera de alcance). El sitio solo puede escribir
esta columna cuando corre con el servidor local (`servidor.py`).
"""

from __future__ import annotations

from guardar import ESTADOS


def aplicar_estado(eventos: list[dict], id_evento: str, estado: str) -> dict:
    """Cambia el estado de un evento en memoria y devuelve el evento.

    Lanza ValueError si el estado no es valido y KeyError si el id no existe.
    No persiste: el llamador decide cuando guardar.
    """
    estado = (estado or "").strip().lower()
    if estado not in ESTADOS:
        raise ValueError(f"estado invalido: {estado!r}")
    buscado = str(id_evento or "").strip()
    if not buscado:
        raise ValueError("id vacio")
    for evento in eventos:
        if str(evento.get("id")) == buscado:
            evento["estado"] = estado
            return evento
    raise KeyError(buscado)
