import pytest

from estado import aplicar_estado


def eventos():
    return [
        {"id": "abc123", "estado": "nuevo"},
        {"id": "def456", "estado": "descartado"},
    ]


def test_cambia_el_estado_del_evento():
    lista = eventos()
    evento = aplicar_estado(lista, "abc123", "confirmado")
    assert evento["id"] == "abc123"
    assert evento["estado"] == "confirmado"
    assert lista[0]["estado"] == "confirmado"


def test_no_toca_los_demas_eventos():
    lista = eventos()
    aplicar_estado(lista, "abc123", "confirmado")
    assert lista[1]["estado"] == "descartado"


def test_acepta_estado_con_espacios_y_mayusculas():
    lista = eventos()
    aplicar_estado(lista, "abc123", "  CONFIRMADO ")
    assert lista[0]["estado"] == "confirmado"


def test_estado_invalido():
    with pytest.raises(ValueError):
        aplicar_estado(eventos(), "abc123", "archivado")


def test_id_inexistente():
    with pytest.raises(KeyError):
        aplicar_estado(eventos(), "nope", "nuevo")


def test_id_vacio():
    with pytest.raises(ValueError):
        aplicar_estado(eventos(), "", "nuevo")


def test_id_numerico_compara_como_texto():
    lista = [{"id": 123, "estado": "nuevo"}]
    aplicar_estado(lista, "123", "confirmado")
    assert lista[0]["estado"] == "confirmado"
