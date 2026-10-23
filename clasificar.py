"""Clasificacion de registros: tipo de remocion en masa y filtro geografico Chile."""

from __future__ import annotations

from comun import contiene, normalizar

# Titulos que anuncian prevencion, riesgo, entrevistas o notas de contexto: no
# son el hecho ocurrido. Solo se descartan si el titulo no trae ademas una
# senal clara de evento consumado.
SENALES_PREVENCION = (
    "riesgo de",
    "alerta por",
    "alertan",
    "advierten",
    "advertir",
    "podrian",
    "recomienda",
    "recomiendan",
    "entrevista",
    "piscinas decantadoras",
    "simulacro",
    "monitorean",
    "se preparan",
    "no se puede descartar",
    "protocolo",
)

SENALES_EVENTO = (
    "dejo",
    "dejando",
    "provoco",
    "afecto",
    "afectando",
    "evacua",
    "evacuan",
    "evacuaron",
    "rescatan",
    "rescataron",
    "rescato",
    "fallecidos",
    "fallecidas",
    "muertos",
    "muertas",
    "heridos",
    "heridas",
    "se registro",
    "ocurrio",
    "se trago",
    "colapso",
    "interrumpio",
    "bloqueo",
    "inundo",
    "anego",
    "destruyo",
    "cayo",
    "se derrumbo",
    "alerta roja",
    "piden evacuar",
    "damnificados",
    "sigue",
    "continua",
    "creciendo",
    "aumentando",
    "reportan",
    "registra",
    "reactivo",
    "reactiva",
    "busqueda",
    "buscan",
    "retoma",
    "retoman",
)


def es_prevencion(titulo_n: str, config: dict) -> bool:
    """True si el titulo es una nota de prevencion/contexto y no un evento."""
    if not titulo_n:
        return False
    cfg = config.get("clasificacion") or {}
    senales = cfg.get("senales_prevencion") or SENALES_PREVENCION
    eventos = cfg.get("senales_evento") or SENALES_EVENTO
    if not any(contiene(titulo_n, s) for s in senales):
        return False
    return not any(contiene(titulo_n, e) for e in eventos)


def _detectar_tipo(texto: str, config: dict) -> tuple[str, str, list[str], dict]:
    """Devuelve (tipo, etiqueta, claves_encontradas, puntaje_por_tipo).

    Puntua cada clave: 2 si es frase (multi-palabra), 1 si es palabra suelta.
    Asi "deslizamiento de nieve" (alud) gana a "deslizamiento" y
    "deslizamiento de lodo" (aluvion) gana a "deslizamiento" a secas.
    """
    puntaje: dict[str, int] = {}
    conteo: dict[str, list[str]] = {}
    etiquetas: dict[str, str] = {}
    posicion: dict[str, int] = {}
    for tipo, defn in (config.get("tipos_evento") or {}).items():
        encontradas = [c for c in defn.get("claves", []) if contiene(texto, c)]
        if encontradas:
            conteo[tipo] = encontradas
            etiquetas[tipo] = defn.get("etiqueta", tipo)
            puntaje[tipo] = sum(2 if " " in c else 1 for c in encontradas)
            posiciones = [texto.find(normalizar(c)) for c in encontradas]
            posicion[tipo] = min(p for p in posiciones if p >= 0)
    if not conteo:
        return "", "", [], {}

    # Mayor puntaje; en empate gana el tipo que aparece primero en el texto
    # ("Socavon en Arauco... aluvion en Juan Riquelme" -> socavon).
    ganador = max(puntaje, key=lambda t: (puntaje[t], -posicion[t]))
    claves = []
    for t in conteo:
        for c in conteo[t]:
            if c not in claves:
                claves.append(c)
    return ganador, etiquetas[ganador], claves, puntaje


def _detectar_geografia(texto: str, config: dict) -> tuple[str, str, bool]:
    """Devuelve (region, comuna, mencion_fuerte_de_chile).

    La comuna se busca en el mapa region -> comunas y se elige la que aparece
    primero en el texto; su region se asigna automaticamente.
    """
    geo = config.get("geografia") or {}
    fuerte = any(contiene(texto, c) for c in geo.get("pais_claves", []))
    fuerte = fuerte or any(contiene(texto, c) for c in geo.get("instituciones_chile", []))

    region = ""
    comuna = ""
    mejor_pos = None
    for entrada in geo.get("regiones", []):
        if isinstance(entrada, str):
            nombre, comunas = entrada, []
        else:
            nombre, comunas = entrada.get("nombre", ""), entrada.get("comunas", [])
        for candidata in comunas:
            if contiene(texto, candidata):
                pos = texto.find(normalizar(candidata))
                if pos >= 0 and (mejor_pos is None or pos < mejor_pos):
                    mejor_pos = pos
                    comuna = candidata
                    region = nombre

    if not region:
        for entrada in geo.get("regiones", []):
            nombre = entrada if isinstance(entrada, str) else entrada.get("nombre", "")
            if nombre and contiene(texto, nombre):
                region = nombre
                break

    return region, comuna, fuerte


def clasificar(registro: dict, config: dict) -> dict | None:
    """Clasifica un registro crudo. Devuelve None si no es una remocion en Chile."""
    titulo_n = normalizar(registro.get("titulo", ""))
    texto = normalizar(f"{registro.get('titulo', '')} {registro.get('descripcion', '')}")
    if not texto:
        return None

    if es_prevencion(titulo_n, config):
        return None

    # Los posts de redes son cortos: se acepta una sola coincidencia en el texto
    # completo. En noticias, en cambio, una palabra suelta en el cuerpo suele ser
    # contexto y no el evento.
    es_red = registro.get("origen") in {"x", "instagram", "facebook"}

    tipo, etiqueta, claves, conteo = _detectar_tipo(titulo_n, config)
    if not tipo:
        tipo, etiqueta, claves, conteo = _detectar_tipo(texto, config)
        if tipo and not es_red and sum(conteo.values()) < 2:
            return None
    if not tipo:
        return None

    region, ciudad, fuerte = _detectar_geografia(texto, config)
    if not fuerte and not (region or ciudad):
        return None

    geo = config.get("geografia") or {}
    extranjero = any(contiene(texto, p) for p in geo.get("paises_excluir", []))
    if not fuerte and extranjero:
        return None

    salida = dict(registro)
    salida.update(
        {
            "tipo_evento": tipo,
            "tipo_etiqueta": etiqueta,
            "keywords": ", ".join(claves),
            "region": region,
            "comuna": ciudad,
        }
    )
    return salida
