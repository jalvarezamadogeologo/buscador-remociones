"""Genera docs/index.html (tabla + mapa Leaflet) a partir de data/eventos.csv.

El HTML es autocontenido en datos: los eventos se incrustan como JSON para que
funcione tanto en GitHub Pages como abierto localmente con file://.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from comun import DOCS, ahora
from guardar import CSV, cargar_eventos

COLORES = {
    "aluvion": "#1f77b4",
    "deslizamiento": "#d62728",
    "caida_rocas": "#ff7f0e",
    "alud": "#9467bd",
    "socavon": "#8c564b",
}

PLANTILLA = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Catastro de remociones en masa - Chile</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
<style>
  :root { --borde:#d9dee5; --texto:#1f2933; --suave:#5b6773; --fondo:#f5f7fa; --acento:#17456b; }
  * { box-sizing: border-box; }
  body { margin:0; font-family: "Segoe UI", Roboto, Arial, sans-serif; color:var(--texto); background:var(--fondo); }
  header { background:var(--acento); color:#fff; padding:18px 22px; }
  header h1 { margin:0 0 4px; font-size:22px; letter-spacing:.2px; }
  header p { margin:0; font-size:13px; opacity:.9; }
  main { padding:16px 22px 40px; max-width:1500px; margin:0 auto; }
  .resumen { display:flex; gap:12px; flex-wrap:wrap; margin:16px 0; }
  .tarjeta { background:#fff; border:1px solid var(--borde); border-radius:8px; padding:12px 16px; min-width:150px; }
  .tarjeta b { display:block; font-size:24px; color:var(--acento); }
  .tarjeta span { font-size:12px; color:var(--suave); text-transform:uppercase; letter-spacing:.4px; }
  .barra { display:flex; gap:10px; flex-wrap:wrap; align-items:flex-end; background:#fff; border:1px solid var(--borde); border-radius:8px; padding:12px; }
  .campo { display:flex; flex-direction:column; gap:4px; }
  .campo label { font-size:11px; text-transform:uppercase; letter-spacing:.4px; color:var(--suave); }
  input, select { font:inherit; font-size:14px; padding:7px 9px; border:1px solid var(--borde); border-radius:6px; background:#fff; color:var(--texto); }
  #buscar { min-width:260px; }
  #mapa { height:420px; margin:16px 0; border:1px solid var(--borde); border-radius:8px; }
  .tabla-wrap { background:#fff; border:1px solid var(--borde); border-radius:8px; overflow:auto; }
  table { border-collapse:collapse; width:100%; font-size:13.5px; }
  th, td { padding:9px 10px; border-bottom:1px solid var(--borde); text-align:left; vertical-align:top; }
  th { background:#eef2f6; font-size:11.5px; text-transform:uppercase; letter-spacing:.4px; color:var(--suave); position:sticky; top:0; }
  tr:last-child td { border-bottom:none; }
  tr:hover td { background:#f8fafc; }
  .tipo { display:inline-block; padding:2px 8px; border-radius:10px; color:#fff; font-size:11.5px; white-space:nowrap; }
  .estado-nuevo { color:#8a5a00; font-weight:600; }
  .estado-confirmado { color:#1b6b3a; font-weight:600; }
  .estado-descartado { color:#8a94a0; text-decoration:line-through; }
  tr.descartado td { opacity:.55; }
  td.titulo a { color:#12507f; }
  .pie { margin-top:14px; font-size:12px; color:var(--suave); display:flex; gap:18px; flex-wrap:wrap; }
  .vacio { padding:28px; text-align:center; color:var(--suave); }
  @media (max-width:700px){ #mapa{height:320px;} header h1{font-size:19px;} }
</style>
</head>
<body>
<header>
  <h1>Catastro de remociones en masa - Chile</h1>
  <p>Deteccion automatica en noticias web. Actualizado: <span id="actualizado">__ACTUALIZADO__</span></p>
</header>
<main>
  <div class="resumen" id="resumen"></div>

  <div class="barra">
    <div class="campo"><label for="buscar">Buscar</label>
      <input id="buscar" type="search" placeholder="Titulo, region, keyword..."></div>
    <div class="campo"><label for="tipo">Tipo</label><select id="tipo"></select></div>
    <div class="campo"><label for="estado">Estado</label><select id="estado"></select></div>
    <div class="campo"><label for="region">Region</label><select id="region"></select></div>
    <div class="campo"><label for="rango">Periodo</label>
      <select id="rango">
        <option value="7">Ultimos 7 dias</option>
        <option value="30">Ultimos 30 dias</option>
        <option value="90" selected>Ultimos 90 dias</option>
        <option value="365">Ultimo anio</option>
        <option value="0">Todo</option>
      </select></div>
  </div>

  <div id="mapa"></div>

  <div class="tabla-wrap">
    <table>
      <thead><tr>
        <th>Fecha</th><th>Tipo</th><th>Titulo</th><th>Region / comuna</th><th>Fuente</th><th>Estado</th>
      </tr></thead>
      <tbody id="filas"></tbody>
    </table>
    <div id="vacio" class="vacio" style="display:none">Sin eventos para los filtros seleccionados.</div>
  </div>

  <div class="pie">
    <span>Datos: <a href="eventos.csv">eventos.csv</a></span>
    <span>Fuentes: Google News RSS, Bing News RSS</span>
    <span>Los eventos son detecciones automaticas y requieren verificacion.</span>
  </div>
</main>

<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script>
const EVENTOS = __DATOS__;
const COLORES = __COLORES__;
const ETIQUETAS = __ETIQUETAS__;

function esc(s){ const d=document.createElement('div'); d.textContent=s==null?'':String(s); return d.innerHTML; }
function fechaCorta(iso){ return iso ? iso.slice(0,16).replace('T',' ') : '-'; }
function claveTipo(t){ return t || 'otro'; }
function colorTipo(t){ return COLORES[t] || '#7f7f7f'; }
function etiquetaTipo(t){ return ETIQUETAS[t] || (t || 'Otro'); }

// ---- mapa ----
const mapa = L.map('mapa',{scrollWheelZoom:false}).setView([-35.5,-71.0],5);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{
  maxZoom:18, attribution:'&copy; OpenStreetMap'
}).addTo(mapa);
const capa = L.layerGroup().addTo(mapa);

// ---- filtros ----
const selTipo=document.getElementById('tipo');
const selEstado=document.getElementById('estado');
const selRegion=document.getElementById('region');
const selRango=document.getElementById('rango');
const inputBuscar=document.getElementById('buscar');

function opciones(sel, valores, etiquetaTodos){
  sel.innerHTML='<option value="">'+etiquetaTodos+'</option>'+valores.map(v=>`<option value="${esc(v)}">${esc(v)}</option>`).join('');
}
const tipos=[...new Set(EVENTOS.map(e=>e.tipo_evento).filter(Boolean))].sort();
const estados=[...new Set(EVENTOS.map(e=>e.estado).filter(Boolean))].sort();
const regiones=[...new Set(EVENTOS.map(e=>e.region).filter(Boolean))].sort();
opciones(selTipo,tipos,'Todos');
opciones(selEstado,estados,'Todos');
opciones(selRegion,regiones,'Todas');

function fechaDe(e){
  const s=e.fecha_publicacion||e.fecha_deteccion||'';
  const t=Date.parse(s);
  return isNaN(t)?null:t;
}
function dentroDeRango(e,dias){
  if(!dias) return true;
  const t=fechaDe(e); if(t===null) return true;
  return t >= Date.now() - dias*86400000;
}

function filtrar(){
  const q=inputBuscar.value.trim().toLowerCase();
  const fTipo=selTipo.value, fEstado=selEstado.value, fRegion=selRegion.value;
  const dias=parseInt(selRango.value,10)||0;
  return EVENTOS.filter(e=>{
    if(fTipo && e.tipo_evento!==fTipo) return false;
    if(fEstado && e.estado!==fEstado) return false;
    if(fRegion && e.region!==fRegion) return false;
    if(!dentroDeRango(e,dias)) return false;
    if(q){
      const txt=[e.titulo,e.descripcion,e.region,e.comuna,e.keywords].join(' ').toLowerCase();
      if(!txt.includes(q)) return false;
    }
    return true;
  });
}

function render(){
  const lista=filtrar();
  // tabla
  const filas=document.getElementById('filas');
  filas.innerHTML=lista.map(e=>{
    const cls=e.estado==='descartado'?' class="descartado"':'';
    const color=colorTipo(e.tipo_evento);
    const enlace=e.url?`<a href="${esc(e.url)}" target="_blank" rel="noopener">${esc(e.titulo)}</a>`:esc(e.titulo);
    return `<tr${cls}>
      <td>${esc(fechaCorta(e.fecha_publicacion||e.fecha_deteccion))}</td>
      <td><span class="tipo" style="background:${color}">${esc(etiquetaTipo(e.tipo_evento))}</span></td>
      <td class="titulo">${enlace}</td>
      <td>${esc(e.region||'-')}${e.comuna?' / '+esc(e.comuna):''}</td>
      <td>${esc(e.fuente||'-')}</td>
      <td class="estado-${esc(e.estado||'nuevo')}">${esc(e.estado||'nuevo')}</td>
    </tr>`;
  }).join('');
  document.getElementById('vacio').style.display=lista.length?'none':'block';

  // mapa
  capa.clearLayers();
  lista.filter(e=>e.lat&&e.lon&&e.estado!=='descartado').forEach(e=>{
    const m=L.circleMarker([parseFloat(e.lat),parseFloat(e.lon)],{
      radius:7, color:'#fff', weight:1.5, fillColor:colorTipo(e.tipo_evento), fillOpacity:.9
    });
    m.bindPopup(`<b>${esc(e.titulo)}</b><br>${esc(etiquetaTipo(e.tipo_evento))} · ${esc(fechaCorta(e.fecha_publicacion||e.fecha_deteccion))}<br>${esc(e.region||'')} ${esc(e.comuna||'')}${e.url?`<br><a href="${esc(e.url)}" target="_blank" rel="noopener">Ver noticia</a>`:''}`);
    m.addTo(capa);
  });

  // resumen
  const porTipo={};
  lista.filter(e=>e.estado!=='descartado').forEach(e=>{
    const t=e.tipo_evento||'otro'; porTipo[t]=(porTipo[t]||0)+1;
  });
  const hace7=EVENTOS.filter(e=>e.estado!=='descartado'&&dentroDeRango(e,7)).length;
  document.getElementById('resumen').innerHTML=
    `<div class="tarjeta"><b>${lista.length}</b><span>Eventos en filtro</span></div>`+
    `<div class="tarjeta"><b>${hace7}</b><span>Ultimos 7 dias</span></div>`+
    Object.keys(porTipo).sort().map(t=>`<div class="tarjeta"><b>${porTipo[t]}</b><span>${esc(etiquetaTipo(t))}</span></div>`).join('');
}
['input','change'].forEach(ev=>{
  inputBuscar.addEventListener(ev,render);
  [selTipo,selEstado,selRegion,selRango].forEach(s=>s.addEventListener(ev,render));
});
render();
</script>
</body>
</html>
"""


def _datos_para_sitio(eventos: list[dict]) -> list[dict]:
    salida = []
    for e in eventos:
        salida.append(
            {
                "id": e.get("id", ""),
                "fecha_publicacion": e.get("fecha_publicacion", ""),
                "fecha_deteccion": e.get("fecha_deteccion", ""),
                "titulo": e.get("titulo", ""),
                "descripcion": (e.get("descripcion", "") or "")[:400],
                "url": e.get("url", ""),
                "fuente": e.get("fuente", ""),
                "tipo_evento": e.get("tipo_evento", ""),
                "tipo_etiqueta": e.get("tipo_etiqueta", ""),
                "region": e.get("region", ""),
                "comuna": e.get("comuna", ""),
                "lat": e.get("lat", ""),
                "lon": e.get("lon", ""),
                "keywords": e.get("keywords", ""),
                "estado": e.get("estado", "nuevo"),
            }
        )
    return salida


def generar_sitio(eventos: list[dict] | None = None, config: dict | None = None) -> Path:
    """Genera docs/index.html y docs/eventos.csv. Devuelve la ruta del HTML."""
    eventos = cargar_eventos() if eventos is None else eventos
    config = config or {}
    DOCS.mkdir(parents=True, exist_ok=True)

    etiquetas = {}
    for tipo, defn in (config.get("tipos_evento") or {}).items():
        etiquetas[tipo] = defn.get("etiqueta", tipo)

    datos = _datos_para_sitio(eventos)
    datos_json = json.dumps(datos, ensure_ascii=False).replace("</", "<\\/")
    colores_json = json.dumps(COLORES, ensure_ascii=False)
    etiquetas_json = json.dumps(etiquetas, ensure_ascii=False)

    html_final = (
        PLANTILLA.replace("__ACTUALIZADO__", ahora().strftime("%Y-%m-%d %H:%M"))
        .replace("__DATOS__", datos_json)
        .replace("__COLORES__", colores_json)
        .replace("__ETIQUETAS__", etiquetas_json)
    )
    destino = DOCS / "index.html"
    destino.write_text(html_final, encoding="utf-8")

    # Copia del CSV para descarga desde el sitio
    if CSV.exists():
        shutil.copyfile(CSV, DOCS / "eventos.csv")

    return destino
