# catastro-remociones

Monitoreo automatico de **remociones en masa recientes en Chile** en noticias web.
Busca en Google News RSS y Bing News (sin API keys), clasifica por tipo de evento,
agrupa las noticias del mismo hecho y conserva hasta 3 fuentes, geocodifica y publica
un catastro versionado + una pagina con mapa.

## Interfaz (docs/index.html)

- **Boton "Actualizar"**:
  - en local con `iniciar.cmd`: ejecuta la busqueda real y recarga datos;
  - en GitHub Pages: vuelve a leer `eventos.json` (ultima version publicada por el workflow).
- **Filtros** aplicados a la vez a la tabla y al mapa: texto libre, tipo (todos los
  tipos de remocion en masa y desbordes/inundaciones), region (las 16 del pais),
  comuna (se habilita al elegir una region y muestra solo sus comunas) y periodo
  en dias como numero entero (0 = todo el historico).
- **Mapa**: zoom con la rueda del mouse, doble clic y botones +/-; selector de capa
  base entre **Calles** (OpenStreetMap), **Hillshade** (Esri) y **Satelite** (Esri).
- **Tabla:** cada fila es un **evento**, no una noticia. La columna "Evento" muestra
  "tipo de remocion + lugar (comuna)"; la columna "Fuentes" despliega hasta 3 enlaces
  con el **nombre del medio** como texto (las primeras que reportaron el hecho).
- **Mapa:** al abrir el popup de un punto se listan los enlaces de sus fuentes, con el
  medio como texto.
- **Boton "Ver"** en cada fila: centra el mapa en el evento y abre su popup
  (deshabilitado si el evento no tiene coordenadas).

## Que genera

- `data/eventos.csv` — catastro (fuente de verdad, editable a mano).
- `data/eventos.json` — espejo JSON del catastro.
- `data/vistos.json` — claves ya procesadas (deduplicacion persistente).
- `data/geocache.json` — cache de geocodificacion (Nominatim).
- `data/georref.json` — coordenadas manuales por lugar (ganan sobre Nominatim).
- `docs/index.html` — buscador autocontenido (tabla + mapa Leaflet + filtros).
- `docs/eventos.json` — datos que lee el boton "Actualizar".
- `docs/eventos.csv` — copia descargable del catastro.
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
```

### Modo local con boton "Actualizar" funcional

```powershell
proyectos\catastro-remociones\iniciar.cmd
```

o directamente:

```powershell
python servidor.py              # http://127.0.0.1:8770
python servidor.py --lookback 48 --puerto 9000
```

El servidor sirve `docs/` y expone `POST /actualizar`: al pulsar el boton, ejecuta
`actualizar.py` y el sitio recarga los datos.

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
- `geografia`: 16 regiones con sus comunas y paises a excluir (evita homonimos). La comuna
  detectada asigna automaticamente su region.
- `fuentes`: Google News, Bing News y feeds RSS directos opcionales.
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
| `estado` | `nuevo` / `confirmado` / `descartado` (lo edita el operador) |
| `issue` | numero de GitHub Issue asociado |

La agrupacion compara tipo, region/comuna y fecha (ventana de 2 dias). Si no hay
lugar, exige similitud de titulo. Se conservan las **3 primeras fuentes** por fecha
de publicacion, para quedarse con los reportes originales y no con derivados tardios.

Los eventos `descartado` no se geocodifican ni se notifican, y no aparecen como
marcadores en el mapa.

## Limitaciones conocidas

- **Redes sociales:** X/Twitter exige API de pago; no se usa. Se puede agregar un feed RSS
  alternativo, pero esas fuentes son fragiles.
- **Falsos positivos:** notas de prevencion o de contexto pueden entrar; el operador los
  marca como `descartado` en el CSV.
- **Agrupacion:** las noticias del mismo hecho se agrupan por tipo + lugar + fecha; si dos
  hechos distintos ocurren en la misma comuna el mismo dia, pueden quedar en un solo evento.
  Se conservan solo 3 fuentes por evento.
- **Geocodificacion:** es aproximada (comuna o region). Para precision, agregar el paraje
  en `data/georref.json`.
- **Texto completo:** se trabaja con titulo y resumen del feed; no se descarga la nota.
