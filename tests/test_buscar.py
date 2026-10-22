from buscar import construir_query
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
