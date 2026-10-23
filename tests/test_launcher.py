import types

import launcher


def test_preparar_entorno_copia_semilla_y_crea_docs(tmp_path, monkeypatch):
    semilla = tmp_path / "semilla"
    semilla.mkdir()
    (semilla / "eventos.csv").write_text("id,estado\n", encoding="utf-8")
    (semilla / "georref.json").write_text("{}", encoding="utf-8")

    monkeypatch.setattr(launcher, "DATA", tmp_path / "data")
    monkeypatch.setattr(launcher, "DOCS", tmp_path / "docs")
    monkeypatch.setattr(launcher, "RECURSOS", tmp_path)
    monkeypatch.setattr(launcher, "cargar_config", lambda: {})
    monkeypatch.setattr(launcher, "guardar_eventos", lambda eventos: None)
    monkeypatch.setattr(
        launcher, "generar_sitio", types.SimpleNamespace(generar_sitio=lambda **kw: None)
    )

    launcher.preparar_entorno()

    assert (tmp_path / "data" / "eventos.csv").read_text(encoding="utf-8") == "id,estado\n"
    assert (tmp_path / "data" / "georref.json").exists()
    assert (tmp_path / "docs").is_dir()


def test_preparar_entorno_sin_semilla_crea_catalogo_vacio(tmp_path, monkeypatch):
    llamadas = []
    monkeypatch.setattr(launcher, "DATA", tmp_path / "data")
    monkeypatch.setattr(launcher, "DOCS", tmp_path / "docs")
    monkeypatch.setattr(launcher, "RECURSOS", tmp_path)
    monkeypatch.setattr(launcher, "cargar_config", lambda: {})
    monkeypatch.setattr(launcher, "guardar_eventos", lambda eventos: llamadas.append(eventos))
    monkeypatch.setattr(
        launcher, "generar_sitio", types.SimpleNamespace(generar_sitio=lambda **kw: None)
    )

    launcher.preparar_entorno()

    assert llamadas == [[]]
    assert (tmp_path / "docs").is_dir()
