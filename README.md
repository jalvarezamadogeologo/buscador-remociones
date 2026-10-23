# buscador-remociones

Monitoreo automatico de **remociones en masa recientes en Chile** en noticias y redes.
Busca en Google News RSS, Bing News y en X/Instagram/Facebook via Google News con
`site:` (todo sin API keys), clasifica por tipo de evento, agrupa las noticias del
mismo hecho y conserva hasta 3 fuentes, geocodifica y publica un catastro versionado
+ una pagina con mapa.

## Interfaz (docs/index.html)

- **Boton "Actualizar"** (en la barra de filtros, a la derecha de "Limpiar filtros"):
  - en local con `iniciar.cmd`: ejecuta la busqueda real y recarga datos;
  - en GitHub Pages: vuelve a leer `eventos.json` (ultima version publicada por el workflow).
  - tras actualizar, el mapa encuadra automaticamente los eventos que cumplen los filtros
    activos (zoom a la capa filtrada; si no hay coordenadas no mueve la vista).
- **Filtros** aplicados a la vez a la tabla y al mapa: texto libre, tipo (todos los
  tipos de remocion en masa y desbordes/inundaciones), **origen** (Prensa o Redes
  sociales), region (las 16 del pais), comuna (se habilita al elegir una region y
  muestra solo sus comunas) y **rango de fechas** `Desde`/`Hasta` sobre la fecha de
  publicacion (vacio = sin limite; ambos inclusive).
  Un evento cuenta como "Redes sociales" cuando **todas** sus fuentes son X/Instagram/
  Facebook; si tiene al menos un medio de prensa, cuenta como "Prensa".
- **Filtros de columna tipo Excel** en los encabezados **Tipo** y **Evento validado**: el
  embudo abre una lista de casillas (los tipos presentes en la tabla; Sí/No para validado)
  y se aplica en vivo a la tabla y al mapa. "Todos" quita el filtro; el embudo queda azul
  cuando hay un filtro activo y "Limpiar filtros" los apaga. Se combinan con los filtros
  de la barra (intersección).
- **Boton "Solo validados"** (barra de filtros): muestra en la tabla y en el mapa solo
  los eventos con la casilla "Evento validado" marcada. Se desactiva con "Limpiar filtros"
  y no borra las marcas.
- **Indicadores de confianza** en la columna "Evento":
  - `sin coords`: el evento no tiene coordenadas, no aparece en el mapa;
  - `solo red`: todas sus fuentes son redes sociales (X/Instagram/Facebook), conviene
    verificarlo en el medio.
- **Mapa**: zoom con la rueda del mouse, doble clic y botones +/-; selector de capa
  base entre **Calles** (OpenStreetMap), **Hillshade** (Esri) y **Satelite** (Esri).
- **Tabla:** cada fila es un **evento**, no una noticia. La columna "Evento" muestra
  "tipo de remocion + lugar (comuna)"; la columna "Fuentes" despliega hasta 3 enlaces
  con el **nombre del medio** como texto (las primeras que reportaron el hecho).
  Los encabezados **Fecha, Tipo, Evento, Region/comuna, Fuentes y Estado** son
  ordenables con un clic (flecha arriba/abajo; segundo clic invierte). El orden inicial
  es fecha descendente. La columna **Estado** es interna y **solo se muestra en modo
  local**; en la version publicada se quita (no se publica el estado de revision).
  La ultima columna, **"Evento validado"**, es una casilla para marcar los eventos que el
  operador da por buenos (se guarda en el navegador, `localStorage`).
- **Descargas** (bajo la tabla), armadas en el navegador (funcionan tambien con `file://`):
  - **Descargar CSV (filtrados):** `remociones_filtradas_AAAA-MM-DD.csv` con los eventos
    que cumplen los filtros actuales, en el orden de la tabla y con las columnas de
    `data/eventos.csv` (BOM + CRLF para Excel).
  - **Descargar CSV (validados):** `remociones_validadas_AAAA-MM-DD.csv` con la cabecera
    del catastro y **solo las filas marcadas**; si no puede leer `eventos.csv` (por
    ejemplo con `file://`), arma el CSV desde los datos embebidos en la pagina. El boton
    muestra el conteo de validados y queda deshabilitado si no hay ninguno.
  - **Descargar KMZ (filtrados):** `remociones_filtradas_AAAA-MM-DD.kmz` (ZIP con `doc.kml`,
    sin librerias) con los eventos filtrados **que tienen coordenadas**.
  - **Descargar KMZ (validados):** `remociones_validadas_AAAA-MM-DD.kmz` con los eventos
    marcados que tienen coordenadas.
  - Ambos KMZ llevan un Placemark por evento y colores por tipo de remocion; se abren en
    Google Earth.
- **Mapa:** al abrir el popup de un punto se listan los enlaces de sus fuentes, con el
  medio como texto.
- **Boton "Ver"** en cada fila: centra el mapa en el evento y abre su popup
  (deshabilitado si el evento no tiene coordenadas).

## Que genera

- `data/eventos.csv` — catastro (fuente de verdad, editable a mano).
- `data/eventos.json` — espejo JSON del catastro.
- `data/vistos.json` — claves ya procesadas (deduplicacion persistente).
- `data/geocache.json` — cache de geocodificacion (Nominatim).
- `data/urlcache.json` — cache de resolucion de enlaces de Google News a la URL del medio.
- `data/georref.json` — coordenadas manuales por lugar (ganan sobre Nominatim).
- `docs/index.html` — buscador autocontenido (tabla + mapa Leaflet + filtros).
- `docs/eventos.json` — datos que lee el boton "Actualizar".
- `docs/eventos.csv` — copia descargable del catastro completo (el boton "Descargar
  Eventos Validados" filtra este archivo en el navegador y entrega solo lo marcado).
- GitHub Issues — un issue por evento nuevo (etiqueta `remocion-en-masa`).

## Uso local

```powershell
python -m pip install -r requirements.txt
python actualizar.py                      # ultimas 24 h (config)
python actualizar.py --lookback 72        # ultimas 72 h
python actualizar.py --dias 7             # ultimos 7 dias
python actualizar.py --sin-notificar      # sin GitHub Issues
python actualizar.py --fuentes google_news
python actualizar.py --sin-geocodificar --max-geocodificaciones 0
python actualizar.py --sin-redes           # no consultar X/Instagram/Facebook
python actualizar.py --sin-resolver        # no resolver enlaces de Google News
python revisar_catastro.py                 # revisar el catalogo existente (prevencion,
                                           # toponimos y fuentes con URL) y regenerar el sitio
python revisar_catastro.py --sin-geocodificar --sin-sitio
python historico.py --dias 120             # barrido historico dia por dia (after/before)
python historico.py --dias 120 --dry-run   # solo informa, no escribe nada
python historico.py --desde 2026-07-01 --hasta 2026-07-31
```

### Barrido historico (ventanas largas)

`actualizar.py --dias 90` y `--dias 120` producen el mismo resultado: Google News RSS
devuelve como maximo **100 entradas por consulta**, asi que `when:Nd` se satura mucho antes
del limite pedido. Medido el 2026-10-23: `when:30d`, `when:90d`, `when:120d` y `when:180d`
entregaron el mismo conjunto de 100 entradas (la mas antigua, 83 dias atras).

Para historia se usa `after:`/`before:`, que si respetan el rango con granularidad de dia.
`historico.py` recorre la ventana en tramos de un dia y alimenta el mismo pipeline
(clasificar, agrupar, geocodificar, resolver enlaces, regenerar sitio):

```powershell
python historico.py --dias 120                  # ~120 consultas, 3-5 min
python historico.py --dias 120 --dry-run        # ver cuantos eventos aparecen sin escribir
python historico.py --dias 120 --sin-geocodificar --sin-sitio --sin-resolver
```

No crea issues salvo `--notificar` ni corre en el workflow. Avisa al final si algun dia
llego al tope de 100 entradas (puede faltar cobertura); separar la consulta por termino
recupera ~60% mas URLs en un dia saturado, pero multiplica las peticiones.

### Enlaces de las fuentes

Google News entrega enlaces `news.google.com/rss/articles/<id>` que en el navegador
responden *"We're sorry... your computer or network may be sending automated queries"*.
El pipeline los resuelve a la URL original del medio (sin API keys, con el RPC interno
`Fbv4je` de Google) antes de guardar y cachea el resultado en `data/urlcache.json`.

Para resolver los enlaces de un catastro ya existente:

```powershell
python resolver_urls.py                    # todos los pendientes (cache incluido)
python resolver_urls.py --maximo 25 --pausa 0.3
python resolver_urls.py --reintentar-fallidos
```

### Modo local: Actualizar y editar Estado

```powershell
proyectos\buscador-remociones\iniciar.cmd
```

o directamente:

```powershell
python servidor.py              # http://127.0.0.1:8770
python servidor.py --lookback 48 --puerto 9000
```

El servidor sirve `docs/` y expone dos endpoints:

- `POST /actualizar`: al pulsar el boton, ejecuta `actualizar.py` y el sitio recarga los datos.
- `POST /estado`: cambia el estado de revision de un evento (`nuevo`, `confirmado` o
  `descartado`). En modo local la columna **Estado** es un selector por fila; al cambiarlo,
  el servidor actualiza `data/eventos.csv`, regenera el sitio y la tabla/mapa se refrescan.
  Al pasar a `descartado` pide confirmacion y el evento deja de mostrarse.

Solo funciona en modo local: **GitHub Pages es estatico y no puede escribir el repositorio**,
asi que en la version publicada la columna Estado no se publica (se quita de la tabla). Los
cambios hechos en local hay que commitearlos y subirlos para que la version publicada los tome.

### Solo ver el sitio (sin servidor)

Abrir `docs/index.html` (funciona con `file://`, pero el boton Actualizar no puede
escribir ni buscar; solo recarga la pagina) o:

```powershell
python -m http.server 8000 --directory docs
```

Tests:

```powershell
python -m pytest -q
```

## Distribucion como ejecutable portable (Windows)

Se empaqueta en una carpeta portable que incluye Python y las dependencias: el usuario
hace doble clic y usa el buscador local, sin instalar nada ni tener cuenta de GitHub.

### Construir

```powershell
pwsh -File build_exe.ps1
```

El script crea `.venv`, instala `requirements.txt` + PyInstaller y genera
`dist\buscador-remociones\` (~23 MB) con el `.exe`, `_internal\` (runtime) y los recursos
empaquetados (`config.yaml` y `semilla/`).

### Usar y compartir

- Se comparte **la carpeta completa** `dist\buscador-remociones\`, no solo el `.exe`.
- Doble clic en `buscador-remociones.exe`: crea `data\`, `docs\` y `config.yaml` junto al
  ejecutable (o en `%LOCALAPPDATA%\buscador-remociones` si la carpeta no es escribible),
  levanta el servidor en un puerto libre y abre el navegador.
- El boton **Actualizar** ejecuta la busqueda real en el mismo equipo (`actualizar.py` en
  el mismo proceso, con `--sin-notificar`); no sube nada a GitHub.
- La primera ejecucion siembra el catalogo desde `semilla/` (copia de `data/`).
- Cerrar la ventana de consola detiene el servidor.

### Firma del ejecutable

El build intenta firmar el `.exe` al final con `firmar_exe.ps1` (certificado de code-signing
del almacen del usuario cuyo sujeto sea "Javier Alvarez Amado"). Para crear el certificado
autofirmado la primera vez:

```powershell
pwsh -File crear_certificado.ps1
```

Notas:
- El certificado queda en `Cert:\CurrentUser\My` (la clave privada no se versiona).
- Un certificado **autofirmado** firma el binario y sella la integridad, pero **no es de
  confianza en otras maquinas**: SmartScreen seguira advirtiendo. Para distribucion real hace
  falta un certificado emitido por una CA (o un servicio como SignPath para open source).
- Si no hay certificado, el build avisa y deja el `.exe` sin firmar.
- Verificar con `Get-AuthenticodeSignature dist\buscador-remociones\buscador-remociones.exe`.

### Limitaciones del ejecutable

- Solo Windows: para Mac/Linux hay que construir en ese sistema.
- `.exe` sin firmar: SmartScreen puede advertir y algunos antivirus marcan falsos positivos
  (se compila con `--noupx` para reducirlos). La solucion definitiva es firmar el binario.
- Nominatim publico: maximo 1 req/s; el pipeline pausa y limita, pero el uso masivo puede
  bloquear la IP.
- Endpoints no oficiales (Google News RSS, Bing News, resolver de Google): pueden cambiar.
- No genera issues ni toca GitHub: el ejecutable trabaja solo con sus datos locales.

## Publicacion en GitHub

1. Crear el repositorio **publico** (Actions ilimitado y Pages gratis) y subir el proyecto.
2. **Settings > Pages**: Source = *Deploy from a branch*, Branch = `main`, Folder = `/docs`.
3. **Settings > Actions > General > Workflow permissions**: marcar *Read and write permissions*
   (el workflow ya declara `contents: write` e `issues: write`).
4. El workflow `.github/workflows/ejecutar.yml` corre solo:
   - programado: `0 */6 * * *` (21:00, 03:00, 09:00 y 15:00 en Chile continental);
   - manual: pestana **Actions > Monitoreo de remociones en masa > Run workflow**,
     con `lookback` (horas) y `notificar` (si/no).
5. Cada corrida busca, actualiza `data/` y `docs/`, y hace commit automatico.

### Monitoreo automatico

Si. Una vez que el workflow esta en el repositorio, GitHub Actions lo ejecuta solo
segun el `cron` configurado (por defecto **cada 6 horas**: 00:00, 06:00, 12:00 y
18:00 UTC, o sea 21:00, 03:00, 09:00 y 15:00 en Chile continental), y ademas se
puede disparar a mano cuando el operador lo requiera. La frecuencia la define el
operador editando el YAML.

Limite de GitHub: el intervalo minimo de un workflow programado es **5 minutos**, pero
GitHub no garantiza puntualidad (puede retrasar u omitir ejecuciones en horas de carga).
A frecuencias altas tambien se castigan las fuentes con demasiadas consultas. El valor
por defecto es 6 horas; si se necesita mas frescura, usar 1 h o 15 min.

Nota: subir `.github/workflows/` requiere que el token de `gh` tenga el scope `workflow`.
Si el push falla con "refusing to allow an OAuth App to create or update workflow",
ejecutar `gh auth refresh -s workflow` y volver a hacer push.

### Frecuencias

Editar el `cron` del workflow:

| Frecuencia | cron |
| --- | --- |
| cada 5 min (minimo de GitHub) | `*/5 * * * *` |
| cada 15 min | `*/15 * * * *` |
| cada 30 min | `*/30 * * * *` |
| cada 1 h | `0 * * * *` |
| cada 6 h | `0 */6 * * *` |
| cada 6 h (por defecto) | `0 */6 * * *` |
| cada 12 h | `0 */12 * * *` |
| 1 vez al dia | `0 11 * * *` |

Notas:

- GitHub puede retrasar ejecuciones programadas; intervalos menores a 15 min no son fiables.
- Los workflows programados se desactivan tras 60 dias sin commits; el commit automatico
  de datos mantiene el repositorio activo.
- El disparo manual (`workflow_dispatch`) sirve para "cuando el operador lo requiera".

## Configuracion (`config.yaml`)

- `tipos_evento`: tipos (aluvion, deslizamiento, caida de rocas, alud, socavon, volcamiento,
  flujo de tierra, avalancha de rocas, desborde/inundacion, lahar, erosion, subsidencia) y
  palabras clave. Las claves se escriben sin tildes; el codigo normaliza el texto.
- `geografia`: 16 regiones con sus comunas, `toponimos` (parajes/sectores para geocodificar
  con precision) y paises a excluir (evita homonimos). La comuna detectada asigna
  automaticamente su region.
- `fuentes`: Google News, Bing News y feeds RSS directos (hoy: La Tercera, Cooperativa,
  The Clinic, La Discusion, El Rancaguino y La Prensa Austral).
- `clasificacion`: opcional; `senales_prevencion` y `senales_evento` para descartar notas
  de prevencion/contexto (por defecto usa las listas del codigo).
- `redes`: busqueda en X, Instagram y Facebook via Google News con `site:` (sin API keys),
  redes activas y maximo de publicaciones por red.
- `consulta.max_terminos`: cuantas palabras sueltas se envian en la busqueda
  (la busqueda evita frases: Google deja de respetar `when:Nd`).
- `deduplicacion`: umbrales para agrupar la misma noticia publicada por varios medios.
- `max_notificaciones` / `max_geocodificaciones`: limites por corrida.

## Modelo de datos (`data/eventos.csv`)

Cada fila es un **evento agrupado** (tipo + lugar + fecha), con hasta 3 fuentes.

| Campo | Descripcion |
| --- | --- |
| `id` | clave del evento (hash de la primera noticia) |
| `fecha_publicacion` | fecha de la fuente mas temprana |
| `fecha_deteccion` | cuando lo detecto el sistema |
| `titulo` | titulo de la primera noticia (uso interno/busqueda) |
| `tipo_evento`, `tipo_etiqueta` | clasificacion |
| `region`, `comuna`, `lat`, `lon` | geografia y coordenadas |
| `fuente_1..3`, `url_1..3`, `fecha_1..3` | hasta 3 fuentes, ordenadas por fecha ascendente |
| `estado` | `nuevo` / `confirmado` / `descartado` (lo edita el operador; la columna Estado solo existe en modo local) |
| `issue` | numero de GitHub Issue asociado |

La agrupacion compara tipo, region/comuna y fecha (ventana de 2 dias). Si no hay
lugar, exige similitud de titulo. Se conservan las **3 primeras fuentes** por fecha
de publicacion, para quedarse con los reportes originales y no con derivados tardios.

Los eventos `descartado` no se geocodifican ni se notifican, y **no se muestran en el
sitio**: quedan fuera de la tabla, del mapa, de los contadores y de las tarjetas.

## Limitaciones conocidas

- **Escritura del Estado:** solo funciona en modo local (`servidor.py`), porque GitHub Pages
  es estatico y no puede modificar el repositorio. Por eso la columna Estado no se publica:
  se quita del sitio en Pages. Para editar en remoto haria falta un backend o un token de
  GitHub en el navegador (no recomendado en una pagina publica).
- **Ventanas largas (`when:Nd`):** Google News RSS entrega como maximo 100 entradas por
  consulta y `when:90d`/`when:120d`/`when:180d` devuelven el mismo conjunto (se satura
  alrededor de los 83 dias y con los resultados mejor rankeados, no los mas recientes).
  Para historia usar `historico.py`, que barre con `after:`/`before:` dia por dia. Los dias
  con mas de 100 entradas en la consulta quedan saturados y pueden perder cobertura; el
  barrido lo informa al final. Bing y los feeds directos no conservan historia.
- **Enlaces de Google News:** se resuelven a la URL del medio; si el RPC interno de Google
  falla o cambia, se conserva el enlace de Google News (que puede mostrar el bloqueo
  "automated queries"). Los fallos quedan cacheados en `data/urlcache.json` y no se
  reintentan salvo con `resolver_urls.py --reintentar-fallidos`.
- **Redes sociales:** se buscan via Google News con `site:` (X, Instagram, Facebook), sin
  API keys. La cobertura depende de lo que Google indexe de cada red y no es tiempo real;
  la API oficial de X es pay-per-use y las de Meta requieren apps/tokens que expiran.
  Algunos enlaces de Facebook/Instagram pueden pedir inicio de sesion.
- **Falsos positivos:** las notas de prevencion/contexto (riesgo, alertas, entrevistas,
  declaraciones) se descartan automaticamente al clasificar; si alguna entra igual, el
  operador la marca como `descartado` en el CSV.
- **Agrupacion:** las noticias del mismo hecho se agrupan por tipo + lugar + fecha; si dos
  hechos distintos ocurren en la misma comuna el mismo dia, pueden quedar en un solo evento.
  Se conservan solo 3 fuentes por evento.
- **Geocodificacion:** usa `geografia.toponimos` (Portillo, Laguna del Inca, Caracoles,
  Juan Riquelme, Higueras...) y `data/georref.json` (coordenadas manuales) antes que la
  comuna/region. Si el toponimo no aparece en el titulo, el punto queda en el centro de la
  comuna. Los eventos sin coordenadas se marcan `sin coords` y no aparecen en el mapa.
- **Texto completo:** se trabaja con titulo y resumen del feed; no se descarga la nota.
