from deduplicar import clave_registro, es_duplicado, jaccard, palabras_clave


def _evento(titulo: str, tipo: str = "aluvion", comuna: str = "Concepcion", fecha: str = "2026-10-22T10:00:00-03:00"):
    return {"titulo": titulo, "tipo_evento": tipo, "comuna": comuna, "fecha_publicacion": fecha}


def test_mismo_evento_titulos_distintos():
    a = _evento("Aluvion en Concepcion: barro cubrio las calles de Juan Riquelme")
    b = _evento("Aluvion deja al menos 10 casas afectadas en Villa Juan Riquelme en Concepcion")
    assert es_duplicado(a, [b])


def test_eventos_distintos_no_se_fusionan():
    a = _evento("Aluvion en Concepcion afecta viviendas en Juan Riquelme")
    b = _evento("Socavon en Arauco mantiene a 150 familias en riesgo", tipo="socavon", comuna="Arauco")
    assert not es_duplicado(a, [b])


def test_clave_estable():
    r = {"titulo": "Aluvion en Concepcion", "url": "https://ejemplo.cl/nota"}
    assert clave_registro(r) == clave_registro(dict(r))


def test_jaccard_basico():
    a = palabras_clave("aluvion en concepcion juan riquelme")
    b = palabras_clave("aluvion en concepcion villa juan riquelme")
    assert 0 < jaccard(a, b) < 1
    assert jaccard(a, a) == 1.0
