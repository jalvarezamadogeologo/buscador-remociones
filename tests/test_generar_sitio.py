import json

import generar_sitio
from comun import cargar_config

CONFIG = cargar_config()


def evento(id_: str = "abc123", **cambios) -> dict:
    base = {
        "id": id_,
        "fecha_publicacion": "2026-10-22T10:00:00-03:00",
        "fecha_deteccion": "2026-10-22T12:00:00-03:00",
        "titulo": "Aluvion en Concepcion",
        "tipo_evento": "aluvion",
        "tipo_etiqueta": "Aluvion / flujo de detritos",
        "region": "Biobio",
        "comuna": "Concepcion",
        "lat": "-36.827070",
        "lon": "-73.050206",
        "fuente_1": "Medio A",
        "url_1": "https://medio-a.cl/nota",
        "fecha_1": "2026-10-22T10:00:00-03:00",
        "fuente_2": "",
        "url_2": "",
        "fecha_2": "",
        "fuente_3": "",
        "url_3": "",
        "fecha_3": "",
        "estado": "nuevo",
        "issue": "",
    }
    base.update(cambios)
    return base


def _generar(tmp_path, monkeypatch, eventos):
    monkeypatch.setattr(generar_sitio, "DOCS", tmp_path)
    monkeypatch.setattr(generar_sitio, "CSV", tmp_path / "eventos.csv")
    return generar_sitio.generar_sitio(eventos, CONFIG)


def test_genera_html_y_json(tmp_path, monkeypatch):
    ruta = _generar(tmp_path, monkeypatch, [evento()])
    assert ruta == tmp_path / "index.html"

    html = (tmp_path / "index.html").read_text(encoding="utf-8")
    datos = json.loads((tmp_path / "eventos.json").read_text(encoding="utf-8"))

    assert datos["total"] == 1
    assert datos["eventos"][0]["fuentes"][0]["medio"] == "Medio A"
    assert "Solo validados" in html
    assert "Evento validado" in html
    assert "Descargar Eventos Validados" in html
    assert "badge-aviso" in html and "badge-red" in html
    assert "ajustarMapaALista" in html
    assert "__DATOS__" not in html


def test_filtro_por_rango_de_fechas_y_orden(tmp_path, monkeypatch):
    _generar(tmp_path, monkeypatch, [evento()])
    html = (tmp_path / "index.html").read_text(encoding="utf-8")
    assert 'id="desde"' in html and 'id="hasta"' in html
    assert 'id="periodo"' not in html
    assert "Periodo (dias)" not in html
    assert "dentroDeFechas" in html
    assert html.count('class="orden"') == 6
    assert "ordenarPor" in html and "actualizarFlechas" in html


def test_botones_de_descarga_y_handler(tmp_path, monkeypatch):
    _generar(tmp_path, monkeypatch, [evento()])
    html = (tmp_path / "index.html").read_text(encoding="utf-8")
    assert "Descargar CSV (filtrados)" in html
    assert "Descargar KMZ" in html
    assert 'id="btn-csv"' in html and 'id="btn-kmz"' in html
    # Cada boton debe tener su listener: el CSV de validados no funcionaba por faltar el suyo.
    assert "btnCsv.addEventListener" in html
    assert "btnKmz.addEventListener" in html
    assert "btnDescargar.addEventListener('click', descargarValidados)" in html
    # KMZ: ZIP minimo con doc.kml armado en el navegador.
    assert "zipUnArchivo('doc.kml'" in html
    assert "0x04034b50" in html and "0x06054b50" in html
    assert "application/vnd.google-earth.kmz" in html
    # El CSV de validados cae a los datos embebidos si no puede leer eventos.csv.
    assert "descargarBlob" in html
    assert "COLUMNAS_CSV" in html


def test_ordena_por_fecha_descendente(tmp_path, monkeypatch):
    _generar(
        tmp_path,
        monkeypatch,
        [
            evento("viejo", fecha_publicacion="2026-10-20T10:00:00-03:00"),
            evento("nuevo", fecha_publicacion="2026-10-22T10:00:00-03:00"),
        ],
    )
    datos = json.loads((tmp_path / "eventos.json").read_text(encoding="utf-8"))
    assert [e["id"] for e in datos["eventos"]] == ["nuevo", "viejo"]


def test_conserva_fuentes_y_estado(tmp_path, monkeypatch):
    _generar(
        tmp_path,
        monkeypatch,
        [
            evento(
                estado="confirmado",
                fuente_2="Medio B",
                url_2="https://medio-b.cl/nota",
                fecha_2="2026-10-22T11:00:00-03:00",
            )
        ],
    )
    datos = json.loads((tmp_path / "eventos.json").read_text(encoding="utf-8"))
    fuentes = datos["eventos"][0]["fuentes"]
    assert [f["medio"] for f in fuentes] == ["Medio A", "Medio B"]
    assert datos["eventos"][0]["estado"] == "confirmado"
