import buscar_redes
from comun import cargar_config

CONFIG = cargar_config()

XML = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Busqueda</title>
    <item>
      <title>Aluvion en Concepcion - X</title>
      <link>https://news.google.com/rss/articles/a</link>
      <description>aluvion en Concepcion</description>
      <pubDate>Thu, 22 Oct 2026 10:00:00 GMT</pubDate>
      <source url="https://x.com">X</source>
    </item>
    <item>
      <title>Nota de otro medio - La Tercera</title>
      <link>https://news.google.com/rss/articles/b</link>
      <description>aluvion en Concepcion</description>
      <pubDate>Thu, 22 Oct 2026 10:00:00 GMT</pubDate>
      <source url="https://latercera.com">La Tercera</source>
    </item>
  </channel>
</rss>
"""


class _Respuesta:
    content = XML.encode("utf-8")

    def raise_for_status(self):
        return None


def test_query_incluye_site_y_ventana():
    query = buscar_redes._query(CONFIG, "x", 24)
    assert "site:x.com" in query
    assert "when:1d" in query


def test_limpia_sufijo_de_la_red():
    assert buscar_redes._limpiar_red("Aluvion en Concepcion - X", "x") == "Aluvion en Concepcion"


def test_solo_acepta_fuentes_de_la_red(monkeypatch):
    monkeypatch.setattr(buscar_redes.requests, "get", lambda *a, **k: _Respuesta())
    registros = buscar_redes.buscar_redes(CONFIG, lookback_horas=24, redes=["x"])
    assert len(registros) == 1
    assert registros[0]["origen"] == "x"
    assert registros[0]["fuente"] == "X"
    assert registros[0]["titulo"] == "Aluvion en Concepcion"
