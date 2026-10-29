# AGENTS.md - buscador-remociones

Monitoreo automatico de remociones en masa recientes en Chile desde noticias web
(Google News RSS y Bing News RSS, sin API keys), con catastro versionado y sitio
estatico con mapa.

## Estructura

- `comun.py` — base compartida: rutas de escritura (proyecto o junto al `.exe`), carga de
  `config.yaml`, normalizacion de texto, fechas de Chile y lectura/escritura atomica de JSON.
- `actualizar.py` — orquestador (buscar, clasificar, deduplicar, geocodificar, guardar, sitio, issues).
- `historico.py` — barrido historico dia por dia con `after:`/`before:` (`--dias N`, `--dry-run`).
- `buscar.py` — fuentes RSS y normalizacion de registros.
- `dominios.py` — filtro de dominios de las fuentes (solo `.cl` y `.com`, con lista de
  exclusion explicita en `config.yaml`) y purga del catalogo existente.
- `buscar_redes.py` — X/Instagram/Facebook via Google News con `site:` (sin API keys).
- `clasificar.py` — tipo de evento y filtro geografico Chile.
- `deduplicar.py` — claves persistentes de noticias procesadas.
- `agrupar.py` — agrupa noticias en eventos (tipo + lugar + fecha) y conserva las 3 primeras fuentes.
- `guardar.py` — `data/eventos.csv` (eventos agrupados) y `eventos.json`.
- `estado.py` — cambia el estado de revision (`nuevo`/`confirmado`/`descartado`) validando
  id y valor.
- `geocodificar.py` — Nominatim + cache + overrides manuales.
- `resolver_url.py` — resuelve enlaces de Google News a la URL del medio (RPC `Fbv4je`) + cache.
- `resolver_urls.py` — CLI para resolver los enlaces del catastro existente y regenerar el sitio.
- `revisar_catastro.py` — mantenimiento: descarte de prevencion/contexto y de hechos que no
  son remociones (techo, muro, metafora, menciones hipoteticas), marca de confianza baja,
  purga de fuentes de dominios ajenos, re-geocodificacion
- `auditar_clasificacion.py` — lista los eventos que la regla descartaria y los marcados con
  `confianza = baja`, con el motivo (revision periodica del catalogo).
  por toponimo y correccion de fuentes guardadas como URL.
- `generar_sitio.py` — `docs/index.html` (tabla + Leaflet).
- `notificar.py` — GitHub Issues.
- `servidor.py` — servidor local: sirve `docs/` y expone `POST /actualizar` y `POST /estado`.
- `launcher.py` — entrada del ejecutable portable: prepara datos, siembra y arranca el servidor.
- `scripts/build_exe.ps1` — construye la carpeta portable en `dist/` con PyInstaller.
- `scripts/crear_certificado.ps1` — crea el certificado autofirmado de code-signing (CurrentUser).
- `scripts/firmar_exe.ps1` — firma el `.exe` con el certificado de code-signing y timestamp.
- `semilla/` — copia inicial de `data/` para el ejecutable (se copia en el primer arranque).
- `config.yaml` — tipos, palabras clave, geografia, fuentes, umbrales.
- `data/` — catastro y estados.
- `docs/` — sitio publicado en GitHub Pages.
- `tests/` - pruebas de pytest (100 casos); el workflow las corre antes de publicar.
- `requirements.txt` — dependencias de ejecucion y pruebas.
- `.github/workflows/ejecutar.yml` — monitoreo programado cada 6 h y publicacion.

## Comandos

```powershell
python actualizar.py --lookback 24 --sin-notificar
python actualizar.py --sin-redes   # sin X/Instagram/Facebook
python actualizar.py --sin-resolver # sin resolver enlaces de Google News
python historico.py --dias 120      # barrido historico (after/before, dia por dia)
python historico.py --dias 120 --dry-run
python resolver_urls.py            # resolver enlaces del catastro existente
python revisar_catastro.py         # prevencion + objeto del hecho + dominios + toponimos
python auditar_clasificacion.py    # que descartaria la regla y que quedo con confianza baja
python servidor.py                 # sitio local: Actualizar y editar Estado (127.0.0.1:8770)
iniciar.cmd                        # lo mismo, doble clic
pwsh -File scripts\build_exe.ps1    # carpeta portable en dist\buscador-remociones
python -m pytest -q
```

## Interfaz

- `docs/index.html`: buscador con filtros (texto, tipo, origen prensa/redes, region, comuna dependiente de
  la region y rango de fechas desde/hasta) aplicados a tabla y mapa; capas base Calles/Hillshade/
  Satelite; zoom con rueda/doble clic/botones; boton "Ver" por fila que centra el mapa.
- Encabezados ordenables (Fecha, Tipo, Evento, Region/comuna, Fuentes, Estado): un clic ordena,
  el segundo invierte; el orden inicial es fecha descendente.
- Filtros de columna tipo Excel en **Tipo** y **Evento validado** (embudo en el encabezado):
  panel de casillas (`abrirPanelFiltro`), aplicacion en vivo, "Todos" y boton azul cuando hay
  filtro. Entran en `filtrar()`, asi que afectan tabla, mapa, contadores y descargas.
- La tabla muestra un evento por fila ("tipo + lugar") y una lista desplegable de hasta
  3 fuentes con el medio como texto. El popup del mapa lista las mismas fuentes.
- Los eventos con `estado=descartado` no se publican: `filtrar()` los excluye, asi que no
  aparecen en la tabla, el mapa, los contadores ni las tarjetas (siguen en el CSV).
- Ultima columna "Evento validado": checkbox por evento; el estado se guarda en
  `localStorage` (`catastro_validados`, mapa id->true), no en el CSV.
- Badge `revisar` en la columna Evento cuando `confianza = baja` (el globo trae el motivo)
  y boton "Solo por revisar" en la barra, que filtra a esos eventos.
- Columna "Estado": es interna y solo se muestra en modo local (`servidor.py`), donde es un
  selector por fila que escribe `data/eventos.csv` via `POST /estado`
  (`estado.aplicar_estado`) y regenera el sitio. En GitHub Pages no se publica: el JS quita
  el encabezado `th.col-estado` y `celdaEstado()` no emite celdas. Al elegir `descartado`
  pide confirmacion; el evento sale de la tabla y del mapa.
- Descargas bajo la tabla, todas armadas en el navegador (sirven con `file://`), cuatro botones:
  "CSV (filtrados)" respeta filtros y orden de la tabla; "CSV (validados)" baja solo las
  filas marcadas (lee `docs/eventos.csv` para conservarlas tal cual y, si no puede, las arma
  desde los datos embebidos); "KMZ (filtrados)" y "KMZ (validados)" generan un ZIP con
  `doc.kml` (Placemarks con coordenadas, color por tipo). Los botones de validados muestran
  el conteo y quedan deshabilitados si no hay marcas.
- Boton "Actualizar": en localhost llama a `POST /actualizar` (servidor.py) y ejecuta
  la busqueda real; en GitHub Pages relee `docs/eventos.json` (ultima version publicada).
  No hay enlace a GitHub en la pagina publica. Vive en la barra de filtros, a la derecha
  de "Limpiar filtros", y al terminar encuadra el mapa en los eventos filtrados
  (`ajustarMapaALista`: `fitBounds` con `maxZoom:12`, o `setView` si hay un solo punto).

## Reglas del proyecto

- No introducir API keys ni servicios de pago.
- Solo se aceptan fuentes de dominios `.cl` y `.com` (`dominios.py`, seccion `dominios` de
  `config.yaml`): corta las noticias extranjeras que comparten toponimos chilenos. El
  dominio se toma de `source.href` en Google News (no gasta el resolver de enlaces). Un
  medio extranjero en `.com` se veta agregandolo a `dominios.excluidos`; si el catalogo ya
  lo tenia, `revisar_catastro.py` lo quita.
- Las palabras clave y busquedas se escriben sin tildes (el codigo normaliza).
- Google News deja de respetar `when:Nd` si la consulta lleva comillas; usar palabras sueltas.
- Google News RSS devuelve como maximo 100 entradas por consulta: `when:90d`, `when:120d` y
  `when:180d` entregan el mismo conjunto. Para historia usar `after:AAAA-MM-DD before:AAAA-MM-DD`
  (granularidad de dia, `after` y `before` inclusivos en Google; el filtro local deja
  `[desde, hasta)` para no solapar tramos). Bing y los feeds directos no conservan historia.
- El operador corrige `estado` en `data/eventos.csv` (`nuevo`/`confirmado`/`descartado`), a
  mano o desde el selector de la columna Estado en modo local. GitHub Pages no escribe.
- No editar a mano `data/vistos.json` salvo para forzar reprocesamiento.
- Las URLs guardadas deben ser del medio, no de Google News (`news.google.com/rss/articles/...`):
  el pipeline las resuelve en cada corrida y `resolver_urls.py` arregla las antiguas. Los
  fallos se cachean en `data/urlcache.json` (valor vacio = no reintentar).
- Clasificacion: las notas de prevencion/contexto (riesgo, alertas, entrevistas, "podrian",
  recomendaciones) se descartan salvo que el titulo tenga una senal de hecho ocurrido
  (`dejo`, `evacuan`, `rescatan`, `sigue`, `creciendo`, `alerta roja`, ...).
- Clasificacion: un techo, un muro o un arbol que se cae no es una remocion en masa. La
  regla del objeto (`clasificar.evaluar_objeto`) descarta el "verbo + objeto" estructural
  sin evidencia de terreno, las metaforas y las menciones hipoteticas ("un posible alud").
  Si el objeto es una vivienda (puede ser la consecuencia de una remocion) o hay un agente
  no geologico (tornado, sismo), el evento entra con `confianza = baja` y badge `revisar`;
  el operador lo confirma con la columna Estado. Ver `auditar_clasificacion.py`.
- Geocodificacion: `geografia.toponimos` + `data/georref.json` tienen prioridad sobre la
  comuna/region. Si agregas un paraje recurrente, sumalo a `toponimos`; si Nominatim lo
  confunde con un homonimo, fija sus coordenadas en `georref.json`.
- El workflow corre `pytest` antes de publicar y avisa por issue (etiqueta `alerta-pipeline`)
  si la resolucion de enlaces se degrada.
- Las descargas del sitio se arman en el navegador y deben funcionar sin servidor (`file://`).
  Cada boton necesita su `addEventListener` (el fallo 2026-10-23 fue justamente un boton sin
  handler). Verificar con Chrome headless interceptando `descargarBlob` que el CSV filtrado,
  el CSV de validados (con y sin `fetch`) y el KMZ se generan; validar el KMZ con `zipfile`.
- Empaquetado: `scripts/build_exe.ps1` genera la carpeta portable (`--onedir --noupx`, incluye
  `tzdata`). En el ejecutable `comun` escribe junto al `.exe` (respaldo `%LOCALAPPDATA%`) y
  el servidor llama `actualizar.main()` en proceso: no hay `actualizar.py` que ejecutar como
  subproceso. Probar el `.exe` dos veces (arranque, GET y POST) antes de compartirlo.
