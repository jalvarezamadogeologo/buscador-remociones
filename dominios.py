"""Filtro de dominios de las fuentes: solo medios en .cl y .com.

Las noticias extranjeras comparten toponimos chilenos (Constitucion, Colina,
Santa Cruz, Los Rios) o mencionan Chile en el resumen, y el clasificador
geografico las dejaba pasar. La regla del proyecto es conservar solo paginas de
dominios .cl y .com; el resto (.com.ar, .com.mx, .pe, .bo, .es, .org, .tv, ...)
se descarta antes de clasificar. `dominios.excluidos` permite vetar ademas
medios extranjeros que usan .com (metrolibre.com, infobae.com, ...).

El filtro usa el dominio que entrega cada fuente sin resolver el enlace: Google
News trae el del medio en `source.href`, Bing y los feeds directos lo traen en
la URL. Asi no se gastan peticiones del resolver en descartar medios ajenos.
"""

from __future__ import annotations

from urllib.parse import urlparse

PERMITIDOS = (".cl", ".com")
INDICES = (1, 2, 3)


def dominio(valor: str | None) -> str:
    """Host normalizado (minusculas, sin credenciales, `www.` ni puerto).

    Acepta una URL completa o un dominio suelto.
    """
    texto = (valor or "").strip().lower()
    if not texto:
        return ""
    if "://" in texto:
        host = urlparse(texto).netloc.lower()
    else:
        host = texto.split("/")[0]
    host = host.rsplit("@", 1)[-1].split(":")[0]
    return host[4:] if host.startswith("www.") else host


def _cfg(config: dict | None) -> dict:
    return (config or {}).get("dominios") or {}


def permitidos(config: dict | None = None) -> tuple[str, ...]:
    """Sufijos de dominio permitidos (por defecto .cl y .com)."""
    valores = _cfg(config).get("permitidos") or PERMITIDOS
    return tuple(str(v).strip().lower() for v in valores if str(v).strip())


def excluidos(config: dict | None = None) -> tuple[str, ...]:
    """Dominios vetados aunque su sufijo este permitido."""
    return tuple(str(v).strip().lower() for v in (_cfg(config).get("excluidos") or []) if str(v).strip())


def permitido(valor: str | None, config: dict | None = None) -> bool:
    """True si el dominio de la fuente esta permitido.

    Un dominio vacio (registro sin URL) se conserva: no hay forma de saberlo y
    descartarlo perderia noticias utiles.
    """
    if _cfg(config).get("activo", True) is False:
        return True
    host = dominio(valor)
    if not host:
        return True
    if any(host == vetado or host.endswith("." + vetado) for vetado in excluidos(config)):
        return False
    return any(host.endswith(sufijo) for sufijo in permitidos(config))


def filtrar(registros: list[dict], config: dict | None = None) -> list[dict]:
    """Quita los registros cuya fuente no es de un dominio permitido."""
    return [
        reg for reg in registros
        if permitido(reg.get("dominio") or reg.get("url") or "", config)
    ]


def purgar_eventos(eventos: list[dict], config: dict | None = None) -> dict:
    """Quita del catalogo las fuentes de dominios no permitidos.

    Reordena las fuentes que quedan (sin huecos) y recalcula la fecha de
    publicacion con la fuente mas temprana. Los eventos que se quedan sin
    ninguna fuente se eliminan: no hay forma de verificarlos.

    Devuelve `{"eventos": <conservados>, "eventos_quitados": n, "fuentes_quitadas": n}`.
    """
    conservados: list[dict] = []
    stats = {"eventos_quitados": 0, "fuentes_quitadas": 0}
    for evento in eventos:
        fuentes = []
        for indice in INDICES:
            medio = evento.get(f"fuente_{indice}") or ""
            url = evento.get(f"url_{indice}") or ""
            if not (medio or url):
                continue
            if not permitido(url or medio, config):
                stats["fuentes_quitadas"] += 1
                continue
            fuentes.append(
                {"medio": medio, "url": url, "fecha": evento.get(f"fecha_{indice}") or ""}
            )
        if not fuentes:
            stats["eventos_quitados"] += 1
            continue
        for indice in INDICES:
            fuente = fuentes[indice - 1] if indice <= len(fuentes) else {"medio": "", "url": "", "fecha": ""}
            evento[f"fuente_{indice}"] = fuente["medio"]
            evento[f"url_{indice}"] = fuente["url"]
            evento[f"fecha_{indice}"] = fuente["fecha"]
        fechas = [f["fecha"] for f in fuentes if f["fecha"]]
        if fechas:
            evento["fecha_publicacion"] = min(fechas)
        conservados.append(evento)
    return {"eventos": conservados, **stats}
