# AGENTS.md - catastro-remociones

Monitoreo automatico de remociones en masa recientes en Chile desde noticias web
(Google News RSS y Bing News RSS, sin API keys), con catastro versionado y sitio
estatico con mapa.

## Estructura

- `actualizar.py` — orquestador (buscar, clasificar, deduplicar, geocodificar, guardar, sitio, issues).
- `buscar.py` — fuentes RSS y normalizacion de registros.
- `clasificar.py` — tipo de evento y filtro geografico Chile.
- `deduplicar.py` — claves persistentes y duplicados entre medios.
- `guardar.py` — `data/eventos.csv` (fuente de verdad) y `eventos.json`.
- `geocodificar.py` — Nominatim + cache + overrides manuales.
- `generar_sitio.py` — `docs/index.html` (tabla + Leaflet).
- `notificar.py` — GitHub Issues.
- `config.yaml` — tipos, palabras clave, geografia, fuentes, umbrales.
- `data/` — catastro y estados.
- `docs/` — sitio publicado en GitHub Pages.

## Comandos

```powershell
python actualizar.py --lookback 24 --sin-notificar
python servidor.py                 # sitio local con boton Actualizar (127.0.0.1:8770)
iniciar.cmd                        # lo mismo, doble clic
python -m pytest -q
```

## Interfaz

- `docs/index.html`: buscador con filtros (texto, tipo, region, comuna dependiente de
  la region y periodo en dias) aplicados a tabla y mapa; capas base Calles/Hillshade/
  Satelite; zoom con rueda/doble clic/botones; boton "Ver" por fila que centra el mapa.
- Boton "Actualizar": en localhost llama a `POST /actualizar` (servidor.py) y ejecuta
  la busqueda real; en GitHub Pages relee `docs/eventos.json` (ultima version publicada).
- "Buscar en GitHub" abre la pestana Actions del repo.

## Reglas del proyecto

- No introducir API keys ni servicios de pago.
- Las palabras clave y busquedas se escriben sin tildes (el codigo normaliza).
- Google News deja de respetar `when:Nd` si la consulta lleva comillas; usar palabras sueltas.
- El operador corrige `estado` en `data/eventos.csv` (`nuevo`/`confirmado`/`descartado`).
- No editar a mano `data/vistos.json` salvo para forzar reprocesamiento.
