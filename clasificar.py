"""Clasificacion de registros: tipo de remocion en masa y filtro geografico Chile."""

from __future__ import annotations

import re

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


# ---------------------------------------------------------------------------
# El objeto del hecho. Un techo, un muro o un arbol que se cae no es una
# remocion en masa, aunque el titulo diga "desprendimiento" o "derrumbe".
# La regla exige el objeto como complemento del verbo ("derrumbe de un muro"),
# no en cualquier parte del titulo: en "socavon se trago un auto" el auto es la
# victima y el evento si es geologico.
# ---------------------------------------------------------------------------

VERBOS_COLAPSO = (
    "derrumbe",
    "derrumbo",
    "desprendimiento",
    "desprendio",
    "caida",
    "cayo",
    "colapso",
    "desplome",
    "desplomo",
)

# Objeto que no pertenece a un proceso de remocion en masa: se descarta.
OBJETOS_NO_GEOLOGICOS = (
    "cielorraso",
    "cielo raso",
    "techo",
    "techos",
    "techumbre",
    "techumbres",
    "cubierta",
    "cubiertas",
    "fachada",
    "fachadas",
    "muro",
    "muros",
    "pandereta",
    "panderetas",
    "cornisa",
    "cornisas",
    "revoque",
    "revoques",
    "alero",
    "aleros",
    "balcon",
    "balcones",
    "escalera",
    "escaleras",
    "andamio",
    "andamios",
    "arbol",
    "arboles",
    "poste",
    "postes",
    "cable",
    "cables",
    "torre",
    "torres",
    "grua",
    "gruas",
    "vidrio",
    "vidrios",
    "ventana",
    "ventanas",
    "reja",
    "rejas",
    "muralla",
    "murallas",
    "camion",
    "camiones",
    "bus",
    "buses",
    "automovil",
    "automoviles",
    "auto",
    "autos",
    "moto",
    "motos",
    "motocicleta",
    "motocicletas",
    "maquinaria",
    "tractor",
    "tractores",
    "ascensor",
    "ascensores",
    "humo",
)

# Objeto que puede ser la consecuencia de una remocion real (una casa que se
# derrumba al pie de un cerro): no se descarta, se marca para revision.
OBJETOS_DE_IMPACTO = (
    "casa",
    "casas",
    "vivienda",
    "viviendas",
    "edificio",
    "edificios",
    "departamento",
    "departamentos",
    "inmueble",
    "inmuebles",
    "estructura",
    "estructuras",
    "colegio",
    "colegios",
    "liceo",
    "liceos",
    "hospital",
    "hospitales",
    "puente",
    "puentes",
    "galpon",
    "galpones",
    "bodega",
    "bodegas",
)

# El terreno se movio: cualquiera de estas palabras da contexto geologico.
EVIDENCIA_TERRENO = (
    "tierra",
    "cerro",
    "ladera",
    "laderas",
    "quebrada",
    "quebradas",
    "talud",
    "taludes",
    "roca",
    "rocas",
    "lodo",
    "barro",
    "pendiente",
    "acantilado",
    "suelo",
    "terreno",
    "terrenos",
    "escombro",
    "escombros",
    "sedimento",
    "sedimentos",
    "relleno",
    "duna",
    "dunas",
    "cauce",
)

# Proceso nombrado explicitamente: el tipo de remocion es el sujeto del hecho.
PROCESO_EXPLICITO = (
    "aluvion",
    "socavon",
    "socavamiento",
    "avalancha",
    "lahar",
    "flujo de detritos",
    "flujo de barro",
    "flujo de tierra",
    "caida de rocas",
    "caida de piedras",
    "deslizamiento de tierra",
    "deslizamiento de lodo",
    "deslizamiento de barro",
    "remocion en masa",
    "movimiento en masa",
    "solifluxion",
    "reptacion",
    "carcavamiento",
    "subsidencia",
)

# Agente que provoca destrozos pero no es una remocion en masa: un tornado no
# es un alud y un temporal no es un aluvion por si solo.
AGENTES_NO_GEOLOGICOS = (
    "tornado",
    "tornados",
    "granizo",
    "granizada",
    "vendaval",
    "tromba",
    "sismo",
    "sismos",
    "terremoto",
    "erupcion",
)

# Mencion hipotetica del proceso ("un posible alud"): no es el hecho ocurrido.
SENALES_HIPOTETICAS = ("posible", "posibles", "eventual", "eventuales", "podria", "podrian")


def _patron_objeto(objetos: tuple[str, ...]) -> str:
    """Patron 'verbo + de/del/en la/en el + (hasta 2 palabras) + objeto'."""
    verbos = "|".join(VERBOS_COLAPSO)
    lista = "|".join(re.escape(o).replace(r"\ ", " ") for o in sorted(objetos, key=len, reverse=True))
    return rf"(?<![a-z0-9])(?:{verbos})[a-z]*\s+(?:de|del|en la|en el)\s+(?:[a-z0-9]+\s+){{0,2}}(?:{lista})(?![a-z0-9])"


_PATRON_NO_GEOLOGICO = re.compile(_patron_objeto(OBJETOS_NO_GEOLOGICOS))
_PATRON_IMPACTO = re.compile(_patron_objeto(OBJETOS_DE_IMPACTO))
_PATRON_METAFORA = re.compile(
    r"(?<![a-z0-9])(?:derrumbe|caida|desplome)\s+(?:del|de)\s+"
    r"(?:sueno|ilusion|mito|relato|modelo|gobierno|proyecto|imperio|promesa)(?![a-z0-9])"
)
_PATRON_HIPOTETICO = re.compile(
    r"(?<![a-z0-9])(?:posible|posibles|eventual|eventuales|podria|podrian)\s+"
    r"(?:aluvion|alud|avalancha|deslizamiento|socavon|remocion|derrumbe|desprendimiento)(?![a-z0-9])"
)


def evaluar_objeto(titulo_n: str) -> tuple[str, str]:
    """Decide si el hecho es una remocion en masa o el colapso de una estructura.

    Devuelve `("descartar" | "revisar" | "ok", motivo)`. Un objeto de impacto
    (casa, vivienda) sin contexto de terreno no se descarta: se marca para
    revision, porque suele ser la consecuencia de una remocion real.
    """
    if not titulo_n:
        return "ok", ""
    if _PATRON_METAFORA.search(titulo_n):
        return "descartar", "metafora u opinion"
    hay_terreno = any(contiene(titulo_n, t) for t in EVIDENCIA_TERRENO)
    hay_proceso = any(contiene(titulo_n, p) for p in PROCESO_EXPLICITO)
    if hay_terreno or hay_proceso:
        return "ok", ""
    for patron, veredicto, motivo in (
        (_PATRON_NO_GEOLOGICO, "descartar", "no es remocion: colapso de una estructura"),
        (_PATRON_IMPACTO, "revisar", "derrumbe de una estructura sin evidencia de terreno"),
    ):
        coincidencia = patron.search(titulo_n)
        if coincidencia:
            return veredicto, f"{motivo} ('{coincidencia.group(0)[:60]}')"
    return "ok", ""


def agente_no_geologico(titulo_n: str) -> str:
    """Nombre del agente que provoca destrozos sin ser remocion (tornado, sismo...)."""
    for agente in AGENTES_NO_GEOLOGICOS:
        if contiene(titulo_n, agente):
            return agente
    return ""


def es_hipotetico(titulo_n: str) -> bool:
    """True si el proceso se menciona como posibilidad ("un posible alud")."""
    return bool(_PATRON_HIPOTETICO.search(titulo_n or ""))



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

    # "Un posible alud" no es el hecho ocurrido. Se mira el titulo, no el
    # resumen: en el cuerpo la mencion hipotetica es contexto.
    if _PATRON_HIPOTETICO.search(titulo_n):
        return None

    # Un techo o un muro que se cae no es una remocion en masa.
    veredicto, motivo = evaluar_objeto(titulo_n)
    if veredicto == "descartar":
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
    confianza = "alta" if veredicto == "ok" else "baja"
    agente = agente_no_geologico(titulo_n)
    if agente and confianza == "alta":
        confianza, motivo = "baja", f"agente no geologico ('{agente}')"
    salida.update(
        {
            "tipo_evento": tipo,
            "tipo_etiqueta": etiqueta,
            "keywords": ", ".join(claves),
            "region": region,
            "comuna": ciudad,
            "confianza": confianza,
            "motivo": motivo,
        }
    )
    return salida
