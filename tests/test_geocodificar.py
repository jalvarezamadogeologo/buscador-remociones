from comun import cargar_config
from geocodificar import geocodificar_eventos, toponimos_detectados

CONFIG = cargar_config()


def _evento(**cambios) -> dict:
    base = {
        "id": "x",
        "titulo": "",
        "region": "",
        "comuna": "",
        "lat": "",
        "lon": "",
        "estado": "nuevo",
    }
    base.update(cambios)
    return base


def test_detecta_toponimo_en_el_titulo():
    evento = _evento(titulo="Avalancha en Portillo deja tres fallecidos")
    assert toponimos_detectados(evento, CONFIG) == ["Portillo"]


def test_prefiere_el_toponimo_mas_largo():
    evento = _evento(titulo="Hallan cuerpo en la Laguna del Inca")
    detectados = toponimos_detectados(evento, CONFIG)
    assert detectados[0] == "Laguna del Inca"


def test_sin_toponimos_devuelve_vacio():
    assert toponimos_detectados(_evento(titulo="Socavon en Concepcion"), CONFIG) == []


def test_geocodifica_con_coordenadas_manuales(tmp_path, monkeypatch):
    monkeypatch.setattr("geocodificar.GEOCACHE", tmp_path / "geocache.json")
    monkeypatch.setattr("geocodificar.time.sleep", lambda _s: None)

    evento = _evento(
        titulo="Avalancha en Portillo",
        region="Valparaiso",
        comuna="Los Andes",
    )
    hechos = geocodificar_eventos([evento], CONFIG, maximo=5)

    assert hechos == 1
    assert evento["lat"].startswith("-32.836")
    assert evento["lon"].startswith("-70.129")


def test_forzar_solo_recalcula_eventos_con_toponimo(tmp_path, monkeypatch):
    monkeypatch.setattr("geocodificar.GEOCACHE", tmp_path / "geocache.json")
    monkeypatch.setattr("geocodificar.time.sleep", lambda _s: None)

    con_toponimo = _evento(
        titulo="Avalancha en Portillo",
        comuna="Los Andes",
        lat="-32.833687",
        lon="-70.598161",
    )
    sin_toponimo = _evento(
        titulo="Socavon en Concepcion",
        comuna="Concepcion",
        lat="-36.827070",
        lon="-73.050206",
    )

    hechos = geocodificar_eventos([con_toponimo, sin_toponimo], CONFIG, maximo=5, forzar=True)

    assert hechos == 1
    assert con_toponimo["lat"].startswith("-32.836")
    assert sin_toponimo["lat"] == "-36.827070"


def test_sin_candidatos_no_consulta(tmp_path, monkeypatch):
    monkeypatch.setattr("geocodificar.GEOCACHE", tmp_path / "geocache.json")

    llamado = []
    monkeypatch.setattr("geocodificar._nominatim", lambda q: llamado.append(q) or None)

    evento = _evento(titulo="Desprendimiento sin lugar")
    assert geocodificar_eventos([evento], CONFIG, maximo=5) == 0
    assert llamado == []
