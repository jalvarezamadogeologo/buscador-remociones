import dominios


def cfg(**cambios):
    base = {"dominios": {"activo": True, "permitidos": [".cl", ".com"], "excluidos": []}}
    base["dominios"].update(cambios)
    return base


def test_dominio_extrae_host_normalizado():
    assert dominios.dominio("https://www.latercera.com/nacional/nota") == "latercera.com"
    assert dominios.dominio("https://biobiochile.cl/nota") == "biobiochile.cl"
    assert dominios.dominio("www.t13.cl") == "t13.cl"
    assert dominios.dominio("latercera.com") == "latercera.com"
    assert dominios.dominio("https://user:clave@Medio.CL:8443/x") == "medio.cl"
    assert dominios.dominio("") == ""
    assert dominios.dominio(None) == ""


def test_permitido_acepta_cl_y_com():
    assert dominios.permitido("https://www.latercera.com/nota", cfg())
    assert dominios.permitido("https://www.cooperativa.cl/nota", cfg())
    assert dominios.permitido("https://x.com/alguien/status/1", cfg())


def test_permitido_rechaza_otros_paises_y_tld():
    for url in (
        "https://www.losandes.com.ar/sociedad/nota",
        "https://nmas.com.mx/nota",
        "https://lapatria.bo/nota",
        "https://rpp.pe/nota",
        "https://salamancahoy.es/nota",
        "https://vietnam.vn/nota",
        "https://aeaclub.org/nota",
        "https://algunmedio.net/nota",
    ):
        assert not dominios.permitido(url, cfg()), url


def test_permitido_conserva_registros_sin_dominio():
    # Sin URL no se puede saber el medio: se conserva.
    assert dominios.permitido("", cfg())
    assert dominios.permitido(None, cfg())


def test_excluidos_veta_com_extranjero_y_subdominios():
    config = cfg(excluidos=["mdzol.com", "infobae.com"])
    assert not dominios.permitido("https://www.mdzol.com/sociedad/nota", config)
    assert not dominios.permitido("https://infobae.com/america/nota", config)
    assert dominios.permitido("https://www.latercera.com/nota", config)
    # No debe vetar un dominio que solo termina parecido.
    assert dominios.permitido("https://noesmdzol.com/nota", config)


def test_activo_false_deja_pasar_todo():
    config = cfg(activo=False, excluidos=["mdzol.com"])
    assert dominios.permitido("https://www.losandes.com.ar/nota", config)
    assert dominios.permitido("https://www.mdzol.com/nota", config)


def test_permitidos_personalizados():
    config = cfg(permitidos=[".cl", ".com", ".ar"])
    assert dominios.permitido("https://www.losandes.com.ar/nota", config)


def test_filtrar_usa_el_dominio_del_registro_antes_que_la_url():
    registros = [
        {"titulo": "chilena", "url": "https://news.google.com/rss/articles/abc", "dominio": "latercera.com"},
        {"titulo": "argentina", "url": "https://news.google.com/rss/articles/def", "dominio": "losandes.com.ar"},
        {"titulo": "sin dominio", "url": "https://biobiochile.cl/nota"},
    ]
    salida = dominios.filtrar(registros, cfg())
    assert [r["titulo"] for r in salida] == ["chilena", "sin dominio"]


def _evento(id_, fuentes, fecha="2026-10-20T10:00:00-03:00"):
    evento = {
        "id": id_,
        "fecha_publicacion": fecha,
        "titulo": "evento de prueba",
        "estado": "nuevo",
    }
    for indice in (1, 2, 3):
        fuente = fuentes[indice - 1] if indice <= len(fuentes) else ("", "", "")
        evento[f"fuente_{indice}"], evento[f"url_{indice}"], evento[f"fecha_{indice}"] = fuente
    return evento


def test_purgar_quita_fuentes_ajenas_y_reordena():
    evento = _evento(
        "abc",
        [
            ("La Tercera", "https://www.latercera.com/nota", "2026-10-19T08:00:00-03:00"),
            ("Los Andes", "https://www.losandes.com.ar/nota", "2026-10-18T08:00:00-03:00"),
            ("Cooperativa", "https://www.cooperativa.cl/nota", "2026-10-20T08:00:00-03:00"),
        ],
    )
    resultado = dominios.purgar_eventos([evento], cfg())
    conservado = resultado["eventos"][0]
    assert resultado["fuentes_quitadas"] == 1
    assert resultado["eventos_quitados"] == 0
    assert conservado["fuente_1"] == "La Tercera"
    assert conservado["fuente_2"] == "Cooperativa"
    assert conservado["fuente_3"] == ""
    assert conservado["url_3"] == ""
    assert conservado["fecha_publicacion"] == "2026-10-19T08:00:00-03:00"


def test_purgar_elimina_eventos_sin_fuentes_permitidas():
    solo_ajena = _evento("xyz", [("Los Andes", "https://www.losandes.com.ar/nota", "2026-10-18T08:00:00-03:00")])
    propia = _evento("abc", [("Cooperativa", "https://www.cooperativa.cl/nota", "2026-10-18T08:00:00-03:00")])
    resultado = dominios.purgar_eventos([solo_ajena, propia], cfg())
    assert resultado["eventos_quitados"] == 1
    assert [e["id"] for e in resultado["eventos"]] == ["abc"]
