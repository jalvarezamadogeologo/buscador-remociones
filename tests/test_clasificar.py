from clasificar import clasificar
from comun import cargar_config

CONFIG = cargar_config()


def reg(titulo: str, descripcion: str = "") -> dict:
    return {
        "titulo": titulo,
        "descripcion": descripcion,
        "url": "",
        "fuente": "test",
        "origen": "test",
        "publicado": None,
    }


def test_aluvion_en_concepcion():
    r = clasificar(reg("Aluvion afecta viviendas en sector Juan Riquelme de Concepcion"), CONFIG)
    assert r is not None
    assert r["tipo_evento"] == "aluvion"
    assert r["comuna"] == "Concepcion"


def test_deslizamiento_de_nieve_es_alud():
    r = clasificar(reg("Rescatan a montanistas tras deslizamiento de nieve en Portillo"), CONFIG)
    assert r is not None
    assert r["tipo_evento"] == "alud"


def test_descarta_evento_en_el_extranjero():
    assert clasificar(reg("Aluvion deja diez muertos en Peru"), CONFIG) is None


def test_descarta_nota_fuera_de_tema():
    assert clasificar(reg("Aumenta el precio del cobre en Chile"), CONFIG) is None


def test_requiere_mencion_geografica_chilena():
    assert clasificar(reg("Deslizamiento bloquea una carretera"), CONFIG) is None
