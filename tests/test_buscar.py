from datetime import date, datetime, timezone

from buscar import (
    _dentro_de_rango,
    construir_query,
    construir_query_rango,
    nombre_medio,
    terminos_consulta,
)
from comun import cargar_config

CONFIG = cargar_config()


def test_query_sin_comillas_y_con_ventana():
    q = construir_query(CONFIG, 24, con_ventana=True)
    assert '"' not in q
    assert "when:1d" in q
    assert " OR " in q


def test_query_sin_ventana_para_bing():
    q = construir_query(CONFIG, 48, con_ventana=False)
    assert "when:" not in q


def test_ventana_en_dias_para_ventanas_largas():
    q = construir_query(CONFIG, 48, con_ventana=True)
    assert "when:2d" in q


def test_nombre_medio_usa_el_dominio_si_la_fuente_es_url():
    assert nombre_medio("https://auroranoticias.cl/") == "auroranoticias.cl"
    assert nombre_medio("https://www.t13.cl/noticia") == "t13.cl"


def test_nombre_medio_conserva_el_nombre():
    assert nombre_medio("Cooperativa") == "Cooperativa"
    assert nombre_medio("  La Tercera  ") == "La Tercera"


def test_nombre_medio_vacio_usa_la_url_del_articulo():
    assert nombre_medio("", "https://www.cnnchile.com/nota") == "cnnchile.com"
    assert nombre_medio("", "") == "Google News"


def test_query_rango_usa_after_before_y_no_when():
    q = construir_query_rango(CONFIG, date(2026, 7, 1), date(2026, 7, 2))
    assert "after:2026-07-01" in q
    assert "before:2026-07-02" in q
    assert "when:" not in q
    assert '"' not in q
    assert " OR " in q


def test_terminos_consulta_respeta_max_terminos_y_sin_frases():
    terminos = terminos_consulta(CONFIG)
    assert terminos
    assert all(" " not in t for t in terminos)
    assert len(terminos) <= int(CONFIG["consulta"]["max_terminos"])


def test_dentro_de_rango_excluye_el_borde_superior():
    desde, hasta = date(2026, 7, 1), date(2026, 7, 2)

    def reg(dia):
        return {"publicado": datetime(2026, 7, dia, 12, tzinfo=timezone.utc)}

    assert _dentro_de_rango(reg(1), desde, hasta) is True
    assert _dentro_de_rango(reg(2), desde, hasta) is False
    assert _dentro_de_rango(reg(30), desde, date(2026, 8, 1)) is True


def test_dentro_de_rango_conserva_registros_sin_fecha():
    assert _dentro_de_rango({"publicado": None}, date(2026, 7, 1), date(2026, 7, 2)) is True
