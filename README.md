# catastro-remociones

Monitoreo automatico de **remociones en masa recientes en Chile** en noticias web.
Busca en Google News RSS y Bing News (sin API keys), clasifica por tipo de evento,
deduplica, geocodifica y publica un catastro versionado + una pagina con mapa.

## Que genera

- `data/eventos.csv` — catastro (fuente de verdad, editable a mano).
- `data/eventos.json` — espejo JSON del catastro.
- `data/vistos.json` — claves ya procesadas (deduplicacion persistente).
- `data/geocache.json` — cache de geocodificacion (Nominatim).
- `data/georref.json` — coordenadas manuales por lugar (ganan sobre Nominatim).
- `docs/index.html` — pagina autocontenida con tabla + mapa Leaflet.
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

Abrir `docs/index.html` en el navegador, o servirlo:

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
   - programado: `0 11 * * *` (07:00 en Chile continental);
   - manual: pestana **Actions > Monitoreo de remociones en masa > Run workflow**,
     con `lookback` (horas) y `notificar` (si/no).
5. Cada corrida busca, actualiza `data/` y `docs/`, y hace commit automatico.

### Frecuencias

Editar el `cron` del workflow:

| Frecuencia | cron |
| --- | --- |
| 1 vez al dia | `0 11 * * *` |
| cada 6 h | `0 */6 * * *` |
| cada 2 h | `0 */2 * * *` |
| cada 1 h | `0 * * * *` |

Notas:

- GitHub puede retrasar ejecuciones programadas; intervalos menores a 15 min no son fiables.
- Los workflows programados se desactivan tras 60 dias sin commits; el commit automatico
  de datos mantiene el repositorio activo.
- El disparo manual (`workflow_dispatch`) sirve para "cuando el operador lo requiera".

## Configuracion (`config.yaml`)

- `tipos_evento`: tipos (aluvion, deslizamiento, caida de rocas, alud, socavon) y palabras clave.
  Las claves se escriben sin tildes; el codigo normaliza el texto.
- `geografia`: regiones/ciudades chilenas y paises a excluir (evita homonimos).
- `fuentes`: Google News, Bing News y feeds RSS directos opcionales.
- `consulta.max_terminos`: cuantas palabras sueltas se envian en la busqueda
  (la busqueda evita frases: Google deja de respetar `when:Nd`).
- `deduplicacion`: umbrales para agrupar la misma noticia publicada por varios medios.
- `max_notificaciones` / `max_geocodificaciones`: limites por corrida.

## Modelo de datos (`data/eventos.csv`)

| Campo | Descripcion |
| --- | --- |
| `id` | hash estable del titulo + dominio |
| `fecha_publicacion` | fecha de la noticia (America/Santiago) |
| `fecha_deteccion` | cuando la detecto el sistema |
| `titulo`, `descripcion`, `url`, `fuente`, `origen` | datos de la noticia |
| `tipo_evento`, `tipo_etiqueta`, `keywords` | clasificacion |
| `region`, `comuna`, `lat`, `lon` | geografia y coordenadas |
| `estado` | `nuevo` / `confirmado` / `descartado` (lo edita el operador) |
| `issue` | numero de GitHub Issue asociado |

Los eventos `descartado` no se geocodifican ni se notifican, y no aparecen como
marcadores en el mapa.

## Limitaciones conocidas

- **Redes sociales:** X/Twitter exige API de pago; no se usa. Se puede agregar un feed RSS
  alternativo, pero esas fuentes son fragiles.
- **Falsos positivos:** notas de prevencion o de contexto pueden entrar; el operador los
  marca como `descartado` en el CSV.
- **Duplicados:** la deduplicacion por similitud reduce, no elimina, las notas repetidas
  del mismo evento entre medios.
- **Geocodificacion:** es aproximada (comuna o region). Para precision, agregar el paraje
  en `data/georref.json`.
- **Texto completo:** se trabaja con titulo y resumen del feed; no se descarga la nota.
