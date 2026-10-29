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

def test_region_se_infiere_de_la_comuna():
    r = clasificar(reg("Aluvion afecta viviendas en Concepcion"), CONFIG)
    assert r is not None
    assert r["comuna"] == "Concepcion"
    assert r["region"] == "Biobio"


def test_inundacion_se_clasifica():
    r = clasificar(reg("Inundacion afecta viviendas en Valparaiso"), CONFIG)
    assert r is not None
    assert r["tipo_evento"] == "desborde_inundacion"


def test_volcamiento_se_clasifica():
    r = clasificar(reg("Volcamiento de estratos en un talud de Coquimbo"), CONFIG)
    assert r is not None
    assert r["tipo_evento"] == "volcamiento"


def test_todas_las_regiones_tienen_comunas():
    regiones = CONFIG["geografia"]["regiones"]
    assert len(regiones) == 16
    assert all(isinstance(r, dict) and r.get("comunas") for r in regiones)

def test_post_de_red_acepta_una_clave_en_la_descripcion():
    registro = {
        "titulo": "Urgente en Las Condes",
        "descripcion": "aluvion en la quebrada",
        "url": "https://x.com/i/status/1",
        "fuente": "X",
        "origen": "x",
        "publicado": None,
    }
    resultado = clasificar(registro, CONFIG)
    assert resultado is not None
    assert resultado["tipo_evento"] == "aluvion"


def test_descarta_nota_de_prevencion():
    assert (
        clasificar(
            reg("Senapred en alerta en el Biobio por riesgo de derrumbe de casas ante tormentas electricas"),
            CONFIG,
        )
        is None
    )


def test_descarta_declaracion_de_prevencion():
    assert (
        clasificar(
            reg("Alcalde de La Reina: las piscinas decantadoras disminuirian las probabilidades de un aluvion"),
            CONFIG,
        )
        is None
    )


def test_no_descarta_evento_con_alerta_y_evacuacion():
    resultado = clasificar(
        reg("Declaran alerta por riesgo de derrumbe y evacuan a 150 familias en Arauco"),
        CONFIG,
    )
    assert resultado is not None
    assert resultado["tipo_evento"] == "deslizamiento"


def test_no_descarta_evento_que_sigue_activo():
    resultado = clasificar(
        reg("Socavon en Constitucion sigue creciendo y vecinos advierten riesgo de nuevos derrumbes"),
        CONFIG,
    )
    assert resultado is not None
    assert resultado["tipo_evento"] == "socavon"


# --- El objeto del hecho: estructuras y metaforas no son remociones ---------


def test_descarta_desprendimiento_de_cielorraso():
    assert (
        clasificar(
            reg("Desprendimiento de cielorraso en el Liceo Oscar Castro reabre el debate en Castro"),
            CONFIG,
        )
        is None
    )


def test_descarta_desprendimiento_de_techo():
    assert clasificar(reg("Desprendimiento de techo en Mallplaza Oeste de Santiago"), CONFIG) is None


def test_descarta_derrumbe_de_muro():
    assert clasificar(reg("Chanaral: calle cerrada tras el derrumbe de un muro en la comuna"), CONFIG) is None


def test_descarta_metafora_de_derrumbe():
    assert clasificar(reg("El derrumbe del sueno venezolano en Chile"), CONFIG) is None


def test_descarta_mencion_hipotetica_de_alud():
    assert (
        clasificar(
            reg("Chile bajo alerta: un tornado causo destrozos y decretaron la emergencia por un posible alud"),
            CONFIG,
        )
        is None
    )


def test_conserva_socavon_que_se_traga_un_auto():
    resultado = clasificar(reg("Socavon se traga un auto en El Bosque, Metropolitana"), CONFIG)
    assert resultado is not None
    assert resultado["tipo_evento"] == "socavon"
    assert resultado["confianza"] == "alta"


def test_conserva_derrumbe_con_evidencia_de_terreno():
    resultado = clasificar(
        reg("Derrumbe de un muro por desprendimiento de tierra en el cerro de Valparaiso"),
        CONFIG,
    )
    assert resultado is not None
    assert resultado["confianza"] == "alta"


def test_derrumbe_de_vivienda_queda_para_revision():
    resultado = clasificar(
        reg("Joven salvo de milagro tras derrumbe de su casa en Vina del Mar"),
        CONFIG,
    )
    assert resultado is not None
    assert resultado["confianza"] == "baja"
    assert "estructura" in resultado["motivo"]


def test_tornado_marca_confianza_baja():
    resultado = clasificar(
        reg("Un tornado destruyo un colegio y un alud agravo la situacion en Requinoa"),
        CONFIG,
    )
    if resultado is not None:
        assert resultado["confianza"] == "baja"
        assert "agente" in resultado["motivo"]

