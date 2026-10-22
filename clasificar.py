"""Clasificacion de registros: tipo de remocion en masa y filtro geografico Chile."""

from __future__ import annotations

from comun import contiene, normalizar


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
    """Devuelve (region, ciudad, mencion_fuerte_de_chile)."""
    geo = config.get("geografia") or {}
    fuerte = any(contiene(texto, c) for c in geo.get("pais_claves", []))
    fuerte = fuerte or any(contiene(texto, c) for c in geo.get("instituciones_chile", []))

    region = ""
    for nombre in geo.get("regiones", []):
        if contiene(texto, nombre):
            region = nombre
            break

    ciudad = ""
    for nombre in geo.get("ciudades", []):
        if contiene(texto, nombre):
            ciudad = nombre
            break

    return region, ciudad, fuerte


def clasificar(registro: dict, config: dict) -> dict | None:
    """Clasifica un registro crudo. Devuelve None si no es una remocion en Chile."""
    titulo_n = normalizar(registro.get("titulo", ""))
    texto = normalizar(f"{registro.get('titulo', '')} {registro.get('descripcion', '')}")
    if not texto:
        return None

    # El titulo es la senal fuerte: evita falsos positivos de notas de contexto
    # (prevencion, politica, economia) que solo mencionan el termino en el cuerpo.
    tipo, etiqueta, claves, conteo = _detectar_tipo(titulo_n, config)
    if not tipo:
        # Desde el cuerpo solo se acepta una senal especifica (frase o >=2 claves):
        # una palabra suelta en el resumen suele ser contexto, no el evento.
        tipo, etiqueta, claves, conteo = _detectar_tipo(texto, config)
        if tipo and sum(conteo.values()) < 2:
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
