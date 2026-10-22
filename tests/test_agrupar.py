from datetime import datetime

from agrupar import agregar_fuente, buscar_evento, crear_evento, etiqueta_evento, fuentes


def _noticia(
    titulo: str,
    url: str,
    fecha: str,
    medio: str,
    tipo: str = "aluvion",
    region: str = "Biobio",
    comuna: str = "Concepcion",
) -> dict:
    return {
        "titulo": titulo,
        "url": url,
        "fuente": medio,
        "publicado": datetime.fromisoformat(fecha),
        "tipo_evento": tipo,
        "tipo_etiqueta": "Aluvion / flujo de detritos",
        "region": region,
        "comuna": comuna,
    }


def test_agrupa_y_ordena_las_tres_primeras_fuentes():
    evento = crear_evento(
        _noticia("A", "https://a.cl", "2026-10-22T10:00:00-03:00", "Medio A"),
        "2026-10-22T12:00:00-03:00",
        "id1",
    )
    agregar_fuente(evento, _noticia("B", "https://b.cl", "2026-10-22T08:00:00-03:00", "Medio B"))
    agregar_fuente(evento, _noticia("C", "https://c.cl", "2026-10-22T09:00:00-03:00", "Medio C"))
    lista = fuentes(evento)
    assert [f["medio"] for f in lista] == ["Medio B", "Medio C", "Medio A"]
    assert evento["fecha_publicacion"].startswith("2026-10-22T08:00")


def test_solo_conserva_tres_fuentes():
    evento = crear_evento(
        _noticia("A", "https://a.cl", "2026-10-22T10:00:00-03:00", "Medio A"),
        "2026-10-22T12:00:00-03:00",
        "id1",
    )
    for i in range(2, 6):
        agregar_fuente(
            evento,
            _noticia(f"N{i}", f"https://n{i}.cl", f"2026-10-22T1{i}:00:00-03:00", f"Medio {i}"),
        )
    assert len(fuentes(evento)) == 3


def test_no_duplica_la_misma_url():
    noticia = _noticia("A", "https://a.cl", "2026-10-22T10:00:00-03:00", "Medio A")
    evento = crear_evento(noticia, "2026-10-22T12:00:00-03:00", "id1")
    assert agregar_fuente(evento, dict(noticia)) is False
    assert len(fuentes(evento)) == 1


def test_eventos_de_distinta_comuna_no_se_agrupan():
    evento = crear_evento(
        _noticia("A", "https://a.cl", "2026-10-22T10:00:00-03:00", "Medio A", comuna="Concepcion"),
        "2026-10-22T12:00:00-03:00",
        "id1",
    )
    otra = _noticia("B", "https://b.cl", "2026-10-22T11:00:00-03:00", "Medio B", comuna="Arauco")
    assert buscar_evento([evento], otra) is None


def test_etiqueta_evento_usa_tipo_y_comuna():
    evento = {"tipo_etiqueta": "Aluvion", "comuna": "Concepcion", "region": "Biobio"}
    assert etiqueta_evento(evento) == "Aluvion en Concepcion"

def test_no_duplica_mismo_medio_y_fecha():
    noticia = _noticia("A", "https://a1.cl", "2026-10-22T10:00:00-03:00", "Cooperativa")
    evento = crear_evento(noticia, "2026-10-22T12:00:00-03:00", "id1")
    otra_url = _noticia("B", "https://a2.cl", "2026-10-22T10:00:00-03:00", "Cooperativa")
    assert agregar_fuente(evento, otra_url) is False
    assert len(fuentes(evento)) == 1

def test_una_fuente_por_medio():
    evento = crear_evento(
        _noticia("A", "https://a1.cl", "2026-10-22T10:00:00-03:00", "BioBioChile"),
        "2026-10-22T12:00:00-03:00",
        "id1",
    )
    otra = _noticia("B", "https://a2.cl", "2026-10-22T11:00:00-03:00", "BioBioChile")
    assert agregar_fuente(evento, otra) is False
    assert len(fuentes(evento)) == 1

def test_agrupa_mismo_evento_hasta_cuatro_dias():
    evento = crear_evento(
        _noticia("A", "https://a.cl", "2026-10-17T15:45:00-03:00", "Medio A", comuna="Portillo"),
        "2026-10-17T16:00:00-03:00",
        "id1",
    )
    otra = _noticia("B", "https://b.cl", "2026-10-21T15:24:00-03:00", "Medio B", comuna="Portillo")
    assert buscar_evento([evento], otra) is evento
