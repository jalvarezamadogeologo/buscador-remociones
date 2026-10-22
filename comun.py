"""Utilidades comunes del catastro de remociones en masa.

Rutas del proyecto, carga de configuracion, normalizacion de texto,
fechas en hora de Chile y lectura/escritura atomica de JSON.
"""

from __future__ import annotations

import html
import json
import os
import re
import tempfile
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

RAIZ = Path(__file__).resolve().parent
DATA = RAIZ / "data"
DOCS = RAIZ / "docs"

ZONA = ZoneInfo("America/Santiago")


def cargar_config(ruta: str | Path | None = None) -> dict:
    """Carga config.yaml (por defecto el del proyecto)."""
    ruta = Path(ruta) if ruta else RAIZ / "config.yaml"
    with open(ruta, encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh) or {}
    return cfg


def normalizar(texto: str | None) -> str:
    """Minusculas, sin tildes, sin puntuacion y con espacios colapsados.

    La enie se convierte en n (NFKD), por eso las claves de config se
    escriben sin tildes ni enie.
    """
    if not texto:
        return ""
    texto = html.unescape(str(texto))
    texto = re.sub(r"<[^>]+>", " ", texto)
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    texto = texto.lower()
    texto = re.sub(r"[^a-z0-9\s]", " ", texto)
    texto = re.sub(r"\s+", " ", texto).strip()
    return texto


def contiene(texto_normalizado: str, clave: str) -> bool:
    """Busca una clave (palabra o frase) en texto ya normalizado."""
    clave_n = normalizar(clave)
    if not clave_n:
        return False
    return re.search(rf"(?<![a-z0-9]){re.escape(clave_n)}(?![a-z0-9])", texto_normalizado) is not None


def limpiar_html(texto: str | None) -> str:
    """Quita etiquetas HTML y colapsa espacios, conservando tildes."""
    if not texto:
        return ""
    texto = re.sub(r"<[^>]+>", " ", str(texto))
    texto = html.unescape(texto)
    return re.sub(r"\s+", " ", texto).strip()


_PREFIJOS_TITULO = re.compile(
    r"^(?:video|videos|en vivo|ultima hora|ultimo minuto|minuto a minuto|"
    r"top\s*\d+|ahora|especial)\s*[|:\-]\s*",
    re.IGNORECASE,
)


def limpiar_titulo(titulo: str | None) -> str:
    """Quita etiquetas HTML y prefijos de seccion ("VIDEO |", "TOP 5 |")."""
    t = limpiar_html(titulo)
    t = _PREFIJOS_TITULO.sub("", t)
    return t.strip(" -|:")


def ahora() -> datetime:
    """Fecha/hora actual en America/Santiago."""
    return datetime.now(ZONA)


def a_iso(dt: datetime | None) -> str:
    """Formatea un datetime en ISO 8601 con offset local."""
    if dt is None:
        return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(ZONA).isoformat(timespec="seconds")


def leer_json(ruta: str | Path, defecto):
    ruta = Path(ruta)
    if not ruta.exists():
        return defecto
    try:
        with open(ruta, encoding="utf-8") as fh:
            return json.load(fh)
    except (json.JSONDecodeError, OSError):
        return defecto


def escribir_json(ruta: str | Path, datos) -> None:
    """Escritura atomica de JSON (UTF-8, indentado)."""
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(ruta.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(datos, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
        os.replace(tmp, ruta)
    except Exception:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def log(msg: str) -> None:
    """Log simple a stdout (visible en GitHub Actions)."""
    print(f"[catastro] {msg}", flush=True)
