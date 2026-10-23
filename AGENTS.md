# AGENTS.md - catastro-remociones

Monitoreo automatico de remociones en masa recientes en Chile desde noticias web
(Google News RSS y Bing News RSS, sin API keys), con catastro versionado y sitio
estatico con mapa.

## Estructura

- `actualizar.py` — orquestador (buscar, clasificar, deduplicar, geocodificar, guardar, sitio, issues).
- `buscar.py` — fuentes RSS y normalizacion de registros.
- `buscar_redes.py` — X/Instagram/Facebook via Google News con `site:` (sin API keys).
- `clasificar.py` — tipo de evento y filtro geografico Chile.
- `deduplicar.py` — claves persistentes de noticias procesadas.
- `agrupar.py` — agrupa noticias en eventos (tipo + lugar + fecha) y conserva las 3 primeras fuentes.
- `guardar.py` — `data/eventos.csv` (eventos agrupados) y `eventos.json`.
- `geocodificar.py` — Nominatim + cache + overrides manuales.
- `resolver_url.py` — resuelve enlaces de Google News a la URL del medio (RPC `Fbv4je`) + cache.
- `resolver_urls.py` — CLI para resolver los enlaces del catastro existente y regenerar el sitio.
- `revisar_catastro.py` — mantenimiento: descarte de prevencion/contexto, re-geocodificacion
  por toponimo y correccion de fuentes guardadas como URL.
- `generar_sitio.py` — `docs/index.html` (tabla + Leaflet).
- `notificar.py` — GitHub Issues.
- `config.yaml` — tipos, palabras clave, geografia, fuentes, umbrales.
- `data/` — catastro y estados.
- `docs/` — sitio publicado en GitHub Pages.

## Comandos

```powershell
python actualizar.py --lookback 24 --sin-notificar
python actualizar.py --sin-redes   # sin X/Instagram/Facebook
python actualizar.py --sin-resolver # sin resolver enlaces de Google News
python resolver_urls.py            # resolver enlaces del catastro existente
python revisar_catastro.py         # prevencion + toponimos + fuentes con URL
python servidor.py                 # sitio local con boton Actualizar (127.0.0.1:8770)
iniciar.cmd                        # lo mismo, doble clic
python -m pytest -q
```

## Interfaz

- `docs/index.html`: buscador con filtros (texto, tipo, origen prensa/redes, region, comuna dependiente de
  la region y periodo en dias) aplicados a tabla y mapa; capas base Calles/Hillshade/
  Satelite; zoom con rueda/doble clic/botones; boton "Ver" por fila que centra el mapa.
- La tabla muestra un evento por fila ("tipo + lugar") y una lista desplegable de hasta
  3 fuentes con el medio como texto. El popup del mapa lista las mismas fuentes.
- Los eventos con `estado=descartado` no se publican: `filtrar()` los excluye, asi que no
  aparecen en la tabla, el mapa, los contadores ni las tarjetas (siguen en el CSV).
- Ultima columna "Evento validado": checkbox por evento; el estado se guarda en
  `localStorage` (`catastro_validados`, mapa id->true), no en el CSV. El boton
  "Descargar Eventos Validados" (bajo la tabla) baja un CSV generado en el navegador
  con la cabecera del catastro y solo las filas marcadas (`eventos_validados_AAAA-MM-DD.csv`,
  con BOM, CRLF y las filas tal cual vienen de `docs/eventos.csv`).
- Boton "Actualizar": en localhost llama a `POST /actualizar` (servidor.py) y ejecuta
  la busqueda real; en GitHub Pages relee `docs/eventos.json` (ultima version publicada).
  No hay enlace a GitHub en la pagina publica. Vive en la barra de filtros, a la derecha
  de "Limpiar filtros", y al terminar encuadra el mapa en los eventos filtrados
  (`ajustarMapaALista`: `fitBounds` con `maxZoom:12`, o `setView` si hay un solo punto).

## Reglas del proyecto

- No introducir API keys ni servicios de pago.
- Las palabras clave y busquedas se escriben sin tildes (el codigo normaliza).
- Google News deja de respetar `when:Nd` si la consulta lleva comillas; usar palabras sueltas.
- El operador corrige `estado` en `data/eventos.csv` (`nuevo`/`confirmado`/`descartado`).
- No editar a mano `data/vistos.json` salvo para forzar reprocesamiento.
- Las URLs guardadas deben ser del medio, no de Google News (`news.google.com/rss/articles/...`):
  el pipeline las resuelve en cada corrida y `resolver_urls.py` arregla las antiguas. Los
  fallos se cachean en `data/urlcache.json` (valor vacio = no reintentar).
- Clasificacion: las notas de prevencion/contexto (riesgo, alertas, entrevistas, "podrian",
  recomendaciones) se descartan salvo que el titulo tenga una senal de hecho ocurrido
  (`dejo`, `evacuan`, `rescatan`, `sigue`, `creciendo`, `alerta roja`, ...).
- Geocodificacion: `geografia.toponimos` + `data/georref.json` tienen prioridad sobre la
  comuna/region. Si agregas un paraje recurrente, sumalo a `toponimos`; si Nominatim lo
  confunde con un homonimo, fija sus coordenadas en `georref.json`.
- El workflow corre `pytest` antes de publicar y avisa por issue (etiqueta `alerta-pipeline`)
  si la resolucion de enlaces se degrada.
