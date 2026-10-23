from resolver_url import (
    construir_cuerpo,
    es_enlace_google_news,
    extraer_parametros,
    id_articulo,
    parsear_destino,
    resolver,
    resolver_eventos,
)

URL = "https://news.google.com/rss/articles/CBMiABC123?oc=5"
HTML = '<c-wiz><div data-n-a-ts="1792763171" data-n-a-sg="AbIaSL_x"></div></c-wiz>'
RESPUESTA = (
    ')]}\'\n\n[["wrb.fr","Fbv4je","[\\"garturlres\\",\\"https://www.medio.cl/nota?x=1\\",1]",'
    'null,null,null,"generic"]]'
)


def test_es_enlace_google_news():
    assert es_enlace_google_news(URL) is True
    assert es_enlace_google_news("https://www.medio.cl/nota") is False
    assert es_enlace_google_news("") is False
    assert es_enlace_google_news(None) is False


def test_id_articulo():
    assert id_articulo(URL) == "CBMiABC123"
    assert id_articulo("https://www.medio.cl/nota") is None


def test_extraer_parametros():
    assert extraer_parametros(HTML) == {"ts": "1792763171", "sg": "AbIaSL_x"}
    assert extraer_parametros("<html></html>") is None


def test_construir_cuerpo():
    cuerpo = construir_cuerpo("CBMiABC123", "1792763171", "AbIaSL_x")
    assert cuerpo.startswith("f.req=")
    assert "Fbv4je" in cuerpo
    assert "CBMiABC123" in cuerpo
    assert "1792763171" in cuerpo


def test_parsear_destino_garturlres():
    assert parsear_destino(RESPUESTA) == "https://www.medio.cl/nota?x=1"


def test_parsear_destino_garturlok_anterior():
    texto = '[["wrb.fr","Fbv4je","[\\"garturlok\\",\\"https://a.cl/n\\",1]",null,null,null,"generic"]]'
    assert parsear_destino(texto) == "https://a.cl/n"


def test_parsear_destino_sin_url():
    assert parsear_destino('[["wrb.fr","Fbv4je",null,null,null,[3],"generic"]]') is None


def test_resolver_ok(monkeypatch):
    monkeypatch.setattr("resolver_url._descargar", lambda url, timeout=15: HTML)
    monkeypatch.setattr("resolver_url._batchexecute", lambda cuerpo, timeout=15: RESPUESTA)
    assert resolver(URL) == "https://www.medio.cl/nota?x=1"


def test_resolver_sin_firma(monkeypatch):
    monkeypatch.setattr("resolver_url._descargar", lambda url, timeout=15: "<html></html>")
    assert resolver(URL) is None


def test_resolver_eventos_usa_cache(tmp_path, monkeypatch):
    llamadas = []

    def falso(url, timeout=15):
        llamadas.append(url)
        return "https://www.medio.cl/nota"

    monkeypatch.setattr("resolver_url.resolver", falso)
    cache = tmp_path / "urlcache.json"
    eventos = [{"url_1": URL, "url_2": "https://www.bing.com/nota", "url_3": ""}]

    stats = resolver_eventos(eventos, maximo=5, pausa=0, cache_path=cache)
    assert stats["resueltos"] == 1 and stats["intentados"] == 1
    assert eventos[0]["url_1"] == "https://www.medio.cl/nota"
    assert eventos[0]["url_2"] == "https://www.bing.com/nota"

    segundo = [{"url_1": URL}]
    stats2 = resolver_eventos(segundo, maximo=5, pausa=0, cache_path=cache)
    assert stats2["cacheados"] == 1
    assert len(llamadas) == 1
    assert segundo[0]["url_1"] == "https://www.medio.cl/nota"


def test_resolver_eventos_respeta_maximo(tmp_path, monkeypatch):
    monkeypatch.setattr("resolver_url.resolver", lambda url, timeout=15: "https://x.cl/a")
    eventos = [{"url_1": f"https://news.google.com/rss/articles/ID{i}?oc=5"} for i in range(3)]

    stats = resolver_eventos(eventos, maximo=1, pausa=0, cache_path=tmp_path / "c.json")
    assert stats["intentados"] == 1
    assert stats["omitidos"] == 2
    assert eventos[1]["url_1"].startswith("https://news.google.com/")


def test_fallos_no_se_reintentan(tmp_path, monkeypatch):
    llamadas = []

    def falso(url, timeout=15):
        llamadas.append(url)
        return None

    monkeypatch.setattr("resolver_url.resolver", falso)
    cache = tmp_path / "c.json"

    primero = [{"url_1": URL}]
    assert resolver_eventos(primero, pausa=0, cache_path=cache)["fallidos"] == 1

    segundo = [{"url_1": URL}]
    stats = resolver_eventos(segundo, pausa=0, cache_path=cache)
    assert stats["intentados"] == 0
    assert len(llamadas) == 1

    tercero = [{"url_1": URL}]
    stats3 = resolver_eventos(tercero, pausa=0, cache_path=cache, reintentar_fallidos=True)
    assert stats3["intentados"] == 1
