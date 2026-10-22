import notificar as modulo


def test_sin_token_no_crea_nada(monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GH_TOKEN", raising=False)
    eventos = [{"id": "a", "estado": "nuevo", "issue": ""}]
    assert modulo.notificar(eventos, {}) == 0


def test_solo_ids_limita_la_notificacion(monkeypatch):
    monkeypatch.setattr(modulo, "_repo", lambda config: "duenio/repo")
    monkeypatch.setattr(modulo, "_token", lambda: "token")
    monkeypatch.setattr(modulo, "asegurar_etiqueta", lambda *a: None)
    monkeypatch.setattr(modulo, "urls_notificadas", lambda *a: set())
    llamados: list[str] = []

    def falso_crear(repo, token, etiqueta, evento):
        llamados.append(evento["id"])
        return 1

    monkeypatch.setattr(modulo, "crear_issue", falso_crear)
    eventos = [
        {"id": "historico", "estado": "nuevo", "issue": ""},
        {"id": "actual", "estado": "nuevo", "issue": ""},
    ]
    creados = modulo.notificar(eventos, {"max_notificaciones": 20}, solo_ids={"actual"})
    assert llamados == ["actual"]
    assert creados == 1
    assert eventos[0]["issue"] == ""
    assert eventos[1]["issue"] == "1"
