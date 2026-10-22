from guardar import COLUMNAS, cargar_eventos, fusionar, guardar_eventos


def test_roundtrip_csv_y_json(tmp_path):
    csv_ruta = tmp_path / "eventos.csv"
    json_ruta = tmp_path / "eventos.json"
    eventos = [
        {
            "id": "abc123",
            "fecha_publicacion": "2026-10-22T10:00:00-03:00",
            "fecha_deteccion": "2026-10-22T12:00:00-03:00",
            "titulo": "Aluvion en Concepcion",
            "descripcion": "Barro en las calles",
            "url": "https://ejemplo.cl/nota",
            "fuente": "Ejemplo",
            "origen": "google_news",
            "tipo_evento": "aluvion",
            "tipo_etiqueta": "Aluvion / flujo de detritos",
            "region": "Biobio",
            "comuna": "Concepcion",
            "lat": "-36.8",
            "lon": "-73.0",
            "keywords": "aluvion",
            "estado": "nuevo",
            "issue": "",
        }
    ]
    guardar_eventos(eventos, csv_ruta=csv_ruta, json_ruta=json_ruta)
    leidos = cargar_eventos(csv_ruta)
    assert len(leidos) == 1
    assert leidos[0]["id"] == "abc123"
    assert set(leidos[0].keys()) == set(COLUMNAS)


def test_fusion_no_duplica_ids(tmp_path):
    a = {"id": "1", "titulo": "A", "fecha_publicacion": "2026-10-22T10:00:00-03:00"}
    b = {"id": "2", "titulo": "B", "fecha_publicacion": "2026-10-21T10:00:00-03:00"}
    assert len(fusionar([a], [a, b])) == 2
