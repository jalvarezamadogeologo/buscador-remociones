from buscar import construir_query, nombre_medio
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
