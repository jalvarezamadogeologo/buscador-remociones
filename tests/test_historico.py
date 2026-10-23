from datetime import date

import buscar
from comun import cargar_config
from historico import rango_dias

CONFIG = cargar_config()

RSS = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel>
<item>
  <title>Aluvion deja viviendas afectadas en Corral - Medio Uno</title>
  <link>https://news.google.com/rss/articles/AAA</link>
  <pubDate>Wed, 01 Jul 2026 12:00:00 GMT</pubDate>
  <source url="https://medio1.cl">Medio Uno</source>
</item>
<item>
  <title>Aluvion deja viviendas afectadas en Corral - Medio Uno</title>
  <link>https://news.google.com/rss/articles/AAA</link>
  <pubDate>Wed, 01 Jul 2026 13:00:00 GMT</pubDate>
  <source url="https://medio1.cl">Medio Uno</source>
</item>
<item>
  <title>Socavon obliga a cortar ruta en Pucon - Medio Dos</title>
  <link>https://news.google.com/rss/articles/BBB</link>
  <pubDate>Thu, 02 Jul 2026 12:00:00 GMT</pubDate>
  <source url="https://medio2.cl">Medio Dos</source>
</item>
</channel></rss>
"""


def test_rango_dias_incluye_el_ultimo_dia():
    tramos = rango_dias(date(2026, 7, 1), date(2026, 7, 3))
    assert tramos == [
        (date(2026, 7, 1), date(2026, 7, 2)),
        (date(2026, 7, 2), date(2026, 7, 3)),
        (date(2026, 7, 3), date(2026, 7, 4)),
    ]


def test_buscar_rango_filtra_por_fecha_y_deduplica(monkeypatch):
    monkeypatch.setattr(buscar, "_descargar", lambda url: RSS)
    registros = buscar.buscar_rango(CONFIG, date(2026, 7, 1), date(2026, 7, 2))
    assert len(registros) == 1
    assert "Corral" in registros[0]["titulo"]
    assert registros[0]["origen"] == "google_news"


def test_buscar_rango_no_consulta_si_google_news_no_esta_activa(monkeypatch):
    monkeypatch.setattr(buscar, "_descargar", lambda url: RSS)
    config = dict(CONFIG)
    config["fuentes"] = dict(config["fuentes"])
    config["fuentes"]["google_news"] = dict(config["fuentes"]["google_news"], activa=False)
    assert buscar.buscar_rango(config, date(2026, 7, 1), date(2026, 7, 2)) == []
