from guardar import COLUMNAS, cargar_eventos, guardar_eventos


def test_roundtrip_csv_y_json(tmp_path):
    csv_ruta = tmp_path / "eventos.csv"
    json_ruta = tmp_path / "eventos.json"
    evento = {columna: "" for columna in COLUMNAS}
    evento.update(
        {
            "id": "abc123",
            "fecha_publicacion": "2026-10-22T10:00:00-03:00",
            "fecha_deteccion": "2026-10-22T12:00:00-03:00",
            "titulo": "Aluvion en Concepcion",
            "tipo_evento": "aluvion",
            "tipo_etiqueta": "Aluvion / flujo de detritos",
            "region": "Biobio",
            "comuna": "Concepcion",
            "fuente_1": "Medio A",
            "url_1": "https://a.cl/nota",
            "fecha_1": "2026-10-22T10:00:00-03:00",
            "estado": "nuevo",
        }
    )
    guardar_eventos([evento], csv_ruta=csv_ruta, json_ruta=json_ruta)
    leidos = cargar_eventos(csv_ruta)
    assert len(leidos) == 1
    assert leidos[0]["id"] == "abc123"
    assert leidos[0]["fuente_1"] == "Medio A"
    assert set(leidos[0].keys()) == set(COLUMNAS)
