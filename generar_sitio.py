"""Genera docs/index.html (buscador con tabla + mapa Leaflet) y docs/eventos.json.

El HTML es autocontenido en datos (funciona abierto con file://) y ademas deja
`eventos.json` junto al HTML para que el boton "Actualizar" refresque los datos
desde GitHub Pages o desde el servidor local.
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path

from agrupar import etiqueta_evento, fuentes
from comun import DOCS, ahora
from guardar import CSV, cargar_eventos, ordenar_eventos

COLORES = {
    "aluvion": "#1f77b4",
    "deslizamiento": "#d62728",
    "caida_rocas": "#ff7f0e",
    "alud": "#9467bd",
    "socavon": "#8c564b",
    "volcamiento": "#e377c2",
    "flujo_tierra": "#17becf",
    "avalancha_rocas": "#bcbd22",
    "desborde_inundacion": "#2ca02c",
    "lahar": "#7f7f7f",
    "erosion": "#aec7e8",
    "subsidencia": "#ffbb78",
}

PLANTILLA = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Buscador de remociones en masa - Chile</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
<style>
  :root { --borde:#d9dee5; --texto:#1f2933; --suave:#5b6773; --fondo:#f5f7fa; --acento:#17456b; }
  * { box-sizing: border-box; }
  body { margin:0; font-family:"Segoe UI",Roboto,Arial,sans-serif; color:var(--texto); background:var(--fondo); }
  header { background:var(--acento); color:#fff; padding:16px 22px; }
  .head-inner { max-width:1500px; margin:0 auto; display:flex; gap:16px; align-items:center; justify-content:space-between; flex-wrap:wrap; }
  header h1 { margin:0 0 4px; font-size:22px; letter-spacing:.2px; }
  header p { margin:0; font-size:13px; opacity:.9; }
  .btn-primario, .btn-mapa { font:inherit; cursor:pointer; border-radius:6px; padding:8px 14px; font-size:14px; }
  .btn-primario { background:var(--acento); color:#fff; border:1px solid var(--acento); font-weight:600; }
  .btn-primario:hover { background:#123a59; }
  .btn-primario:disabled { opacity:.65; cursor:wait; }
  #btn-descargar:disabled { cursor:not-allowed; }
  .btn-mapa { background:#eef4fa; color:var(--acento); border:1px solid #c8d8e8; padding:4px 10px; font-size:12.5px; }
  .btn-mapa:hover { background:#dcebf8; }
  main { padding:0 22px 40px; max-width:1500px; margin:0 auto; }
  .estado { display:none; margin:12px 0 0; padding:9px 12px; border-radius:6px; background:#e8f1f8; color:#17456b; font-size:13.5px; border:1px solid #c8ddef; }
  .estado.visible { display:block; }
  .resumen { display:flex; gap:12px; flex-wrap:wrap; margin:16px 0; }
  .tarjeta { background:#fff; border:1px solid var(--borde); border-radius:8px; padding:12px 16px; min-width:150px; }
  .tarjeta b { display:block; font-size:24px; color:var(--acento); }
  .tarjeta span { font-size:12px; color:var(--suave); text-transform:uppercase; letter-spacing:.4px; }
  .barra { display:flex; gap:10px; flex-wrap:wrap; align-items:flex-end; background:#fff; border:1px solid var(--borde); border-radius:8px; padding:12px; }
  .campo { display:flex; flex-direction:column; gap:4px; }
  .campo label { font-size:11px; text-transform:uppercase; letter-spacing:.4px; color:var(--suave); }
  input, select { font:inherit; font-size:14px; padding:7px 9px; border:1px solid var(--borde); border-radius:6px; background:#fff; color:var(--texto); }
  #buscar { min-width:250px; }
  #periodo { width:110px; }
  select:disabled { background:#f0f2f5; color:#9aa5b1; cursor:not-allowed; }
  .btn-limpiar { background:#fff; color:var(--suave); border:1px solid var(--borde); cursor:pointer; font:inherit; font-size:13.5px; padding:8px 12px; border-radius:6px; }
  .btn-limpiar.activo { background:var(--acento); color:#fff; border-color:var(--acento); }
  .badge { display:inline-block; margin-left:6px; padding:1px 6px; border-radius:8px; font-size:10.5px; text-transform:uppercase; letter-spacing:.3px; vertical-align:middle; white-space:nowrap; }
  .badge-aviso { background:#fff4e0; color:#8a5a00; border:1px solid #f0d9a8; }
  .badge-red { background:#eef4fa; color:#17456b; border:1px solid #c8d8e8; }
  #mapa { height:480px; margin:16px 0; border:1px solid var(--borde); border-radius:8px; }
  .tabla-wrap { background:#fff; border:1px solid var(--borde); border-radius:8px; overflow:auto; }
  table { border-collapse:collapse; width:100%; font-size:13.5px; }
  th, td { padding:9px 10px; border-bottom:1px solid var(--borde); text-align:left; vertical-align:top; }
  th { background:#eef2f6; font-size:11.5px; text-transform:uppercase; letter-spacing:.4px; color:var(--suave); position:sticky; top:0; }
  tr:last-child td { border-bottom:none; }
  tr:hover td { background:#f8fafc; }
  tr.validado td { background:#f1f8f3; }
  tr.validado:hover td { background:#e9f4ec; }
  .tipo { display:inline-block; padding:2px 8px; border-radius:10px; color:#fff; font-size:11.5px; white-space:nowrap; }
  .estado-nuevo { color:#8a5a00; font-weight:600; }
  .estado-confirmado { color:#1b6b3a; font-weight:600; }
  .estado-descartado { color:#8a94a0; text-decoration:line-through; }
  tr.descartado td { opacity:.55; }
  td.titulo a { color:#12507f; }
  .col-mapa { text-align:center; white-space:nowrap; }
  .col-validar { text-align:center; white-space:nowrap; }
  .chk-validar { width:17px; height:17px; cursor:pointer; accent-color:#17456b; vertical-align:middle; }
  td.col-validar { text-align:center; }
  .descarga { display:flex; gap:12px; align-items:center; flex-wrap:wrap; margin:14px 0 0; }
  .descarga-ayuda { font-size:12.5px; color:var(--suave); }
  .sin-coords { color:#a6b0ba; }
  .fuentes-det summary { cursor:pointer; color:#12507f; font-size:12.5px; }
  .fuentes-det ul { margin:6px 0 0 16px; padding:0; }
  .fuentes-det li { margin:2px 0; }
  .pie { margin-top:14px; font-size:12px; color:var(--suave); display:flex; gap:18px; flex-wrap:wrap; }
  .vacio { padding:28px; text-align:center; color:var(--suave); }
  @media (max-width:760px){ #mapa{height:340px;} header h1{font-size:19px;} #buscar{min-width:170px;} }
</style>
</head>
<body>
<header>
  <div class="head-inner">
    <div>
      <h1>Buscador de remociones en masa - Chile</h1>
      <p>Deteccion automatica en noticias web. Actualizado: <span id="actualizado">__ACTUALIZADO__</span></p>
    </div>
  </div>
</header>
<main>
  <div id="estado" class="estado"></div>
  <div class="resumen" id="resumen"></div>

  <div class="barra">
    <div class="campo"><label for="buscar">Buscar</label>
      <input id="buscar" type="search" placeholder="Titulo, lugar, keyword..."></div>
    <div class="campo"><label for="tipo">Tipo</label><select id="tipo"></select></div>
    <div class="campo"><label for="region">Region</label><select id="region"></select></div>
    <div class="campo"><label for="comuna">Comuna</label><select id="comuna" disabled></select></div>
    <div class="campo"><label for="periodo">Periodo (dias)</label>
      <input id="periodo" type="number" min="0" step="1" value="90" title="0 = todo el historico"></div>
    <button id="btn-limpiar" class="btn-limpiar" type="button">Limpiar filtros</button>
    <button id="btn-validados" class="btn-limpiar" type="button" aria-pressed="false">Solo validados</button>
    <button id="btn-actualizar" class="btn-primario" type="button">Actualizar</button>
  </div>

  <div id="mapa"></div>

  <div class="tabla-wrap">
    <table>
      <thead><tr>
        <th>Fecha</th><th>Tipo</th><th>Evento</th><th>Region / comuna</th><th>Fuentes</th><th>Estado</th><th class="col-mapa">Mapa</th><th class="col-validar">Evento validado</th>
      </tr></thead>
      <tbody id="filas"></tbody>
    </table>
    <div id="vacio" class="vacio" style="display:none">Sin eventos para los filtros seleccionados.</div>
  </div>

  <div class="descarga">
    <button id="btn-descargar" class="btn-primario" type="button">Descargar Eventos Validados</button>
    <span class="descarga-ayuda">Incluye solo los eventos con la casilla "Evento validado" marcada.</span>
  </div>

  <div class="pie">
    <span id="contador">0 de 0 eventos</span>
    <span>Fuentes: Google News RSS, Bing News RSS</span>
    <span>Las detecciones automaticas requieren verificacion.</span>
  </div>
</main>

<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script>
let EVENTOS = __DATOS__;
let ACTUALIZADO = "__ACTUALIZADO__";
const TIPOS = __TIPOS__;
const REGIONES = __REGIONES__;
const COLORES = __COLORES__;
const ES_LOCAL = ["127.0.0.1", "localhost"].includes(location.hostname);
const CLAVE_VALIDADOS = 'catastro_validados';
let VALIDADOS = (()=>{
  try { const d = JSON.parse(localStorage.getItem(CLAVE_VALIDADOS) || '{}'); return (d && typeof d==='object') ? d : {}; }
  catch (e) { return {}; }
})();
function esValidado(id){ return VALIDADOS[String(id)] === true; }
function guardarValidados(){ try { localStorage.setItem(CLAVE_VALIDADOS, JSON.stringify(VALIDADOS)); } catch (e) {} }
function contarValidados(){ return Object.keys(VALIDADOS).filter(k=>VALIDADOS[k]).length; }
function refrescarBotonDescarga(){
  const n = contarValidados();
  btnDescargar.textContent = 'Descargar Eventos Validados' + (n ? ' (' + n + ')' : '');
  btnDescargar.disabled = n === 0;
}
function marcarValidado(id, valor){
  if (valor) VALIDADOS[String(id)] = true; else delete VALIDADOS[String(id)];
  guardarValidados();
  refrescarBotonDescarga();
}

function esc(s){ const d=document.createElement('div'); d.textContent=s==null?'':String(s); return d.innerHTML; }
function norm(s){ return (s||'').toString().normalize('NFD').replace(/[\\u0300-\\u036f]/g,'').toLowerCase(); }
function fechaCorta(iso){ return iso ? iso.slice(0,16).replace('T',' ') : '-'; }
function fechaMs(e){ const s=e.fecha_publicacion||e.fecha_deteccion||''; const t=Date.parse(s); return isNaN(t)?null:t; }
function dentroDeRango(e,dias){ if(!dias) return true; const t=fechaMs(e); return t===null || t >= Date.now()-dias*86400000; }
function colorTipo(t){ return COLORES[t] || '#7f7f7f'; }
function etiquetaTipo(t){ return TIPOS[t] || (t || 'Otro'); }
function tieneCoords(e){ return e.lat !== '' && e.lon !== '' && e.lat != null && e.lon != null; }
function esRedSocial(url){
  const u = (url||'').toLowerCase();
  return ['instagram.com','facebook.com','x.com','twitter.com'].some(d=>u.includes(d));
}

// ---- mapa: capas base seleccionables (calles, hillshade, satelite) ----
const mapa = L.map('mapa', {scrollWheelZoom:true, zoomControl:true, doubleClickZoom:true, touchZoom:true}).setView([-35.5,-71.0],5);
const capasBase = {
  "Calles": L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom:18, attribution:'&copy; OpenStreetMap'
  }),
  "Hillshade": L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/Elevation/World_Hillshade/MapServer/tile/{z}/{y}/{x}', {
    maxZoom:18, attribution:'Esri, USGS, NOAA'
  }),
  "Satelite": L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
    maxZoom:18, attribution:'Esri, Maxar, Earthstar Geographics'
  })
};
capasBase["Calles"].addTo(mapa);
L.control.layers(capasBase, null, {position:'topright'}).addTo(mapa);
L.control.scale({imperial:false, position:'bottomleft'}).addTo(mapa);

const capa = L.layerGroup().addTo(mapa);
const marcadores = new Map();

const buscar = document.getElementById('buscar');
const selTipo = document.getElementById('tipo');
const selRegion = document.getElementById('region');
const selComuna = document.getElementById('comuna');
const inputPeriodo = document.getElementById('periodo');
const filas = document.getElementById('filas');
const btnActualizar = document.getElementById('btn-actualizar');
const btnDescargar = document.getElementById('btn-descargar');
const btnValidados = document.getElementById('btn-validados');
const cajaEstado = document.getElementById('estado');
let soloValidados = false;

function opciones(sel, valores, etiquetaTodos){
  const prev = sel.value;
  sel.innerHTML = '<option value="">'+etiquetaTodos+'</option>' +
    valores.map(v=>`<option value="${esc(v)}">${esc(v)}</option>`).join('');
  sel.value = valores.includes(prev) ? prev : '';
}

function poblarComunas(){
  const region = selRegion.value;
  if (!region){
    selComuna.innerHTML = '<option value="">Selecciona una region</option>';
    selComuna.value = '';
    selComuna.disabled = true;
    return;
  }
  const comunas = [...new Set(
    EVENTOS.filter(e=>e.region===region).map(e=>e.comuna).filter(Boolean)
  )].sort((a,b)=>a.localeCompare(b,'es'));
  const prev = selComuna.value;
  selComuna.disabled = false;
  selComuna.innerHTML = '<option value="">Todas</option>' +
    comunas.map(c=>`<option value="${esc(c)}">${esc(c)}</option>`).join('');
  selComuna.value = comunas.includes(prev) ? prev : '';
}

function poblarFiltros(){
  opciones(selTipo, Object.keys(TIPOS), 'Todos');
  opciones(selRegion, REGIONES, 'Todas');
  poblarComunas();
}

function filtrar(){
  const q = norm(buscar.value.trim());
  const dias = parseInt(inputPeriodo.value, 10);
  const ventana = (isNaN(dias) || dias < 0) ? 0 : dias;
  return EVENTOS.filter(e=>{
    if (soloValidados && !esValidado(e.id)) return false;
    if (selTipo.value && e.tipo_evento !== selTipo.value) return false;
    if (selRegion.value && e.region !== selRegion.value) return false;
    if (selComuna.value && e.comuna !== selComuna.value) return false;
    if (!dentroDeRango(e, ventana)) return false;
    if (q){
      const medios = (e.fuentes || []).map(f=>f.medio).join(' ');
      const txt = norm([e.evento, e.titulo, e.region, e.comuna, e.tipo_etiqueta, medios].join(' '));
      if (!txt.includes(q)) return false;
    }
    return true;
  });
}

function enfocar(id){
  const e = EVENTOS.find(x=>String(x.id)===String(id));
  if (!e || !tieneCoords(e)) return;
  mapa.setView([parseFloat(e.lat), parseFloat(e.lon)], 12, {animate:true});
  const m = marcadores.get(String(e.id));
  if (m) m.openPopup();
  document.getElementById('mapa').scrollIntoView({behavior:'smooth', block:'center'});
}

// Zoom a la capa: encuadra el mapa en los eventos que cumplen los filtros actuales.
// Sin animacion: el encuadre debe quedar aplicado aunque el mapa no este visible.
function ajustarMapaALista(lista){
  const puntos = (lista||[])
    .filter(e=>tieneCoords(e) && e.estado!=='descartado')
    .map(e=>[parseFloat(e.lat), parseFloat(e.lon)]);
  if (!puntos.length) return false;
  if (puntos.length === 1){
    mapa.setView(puntos[0], 12, {animate:false});
  } else {
    mapa.fitBounds(L.latLngBounds(puntos), {padding:[40,40], maxZoom:12, animate:false});
  }
  return true;
}

function detallesFuentes(lista){
  if (!lista || !lista.length) return '<span class="sin-coords">-</span>';
  const items = lista.map(f=>{
    const medio = esc(f.medio || 'Fuente');
    return f.url
      ? `<li><a href="${esc(f.url)}" target="_blank" rel="noopener">${medio}</a></li>`
      : `<li>${medio}</li>`;
  }).join('');
  return `<details class="fuentes-det"><summary>${lista.length} fuente${lista.length===1?'':'s'}</summary><ul>${items}</ul></details>`;
}

function render(){
  const lista = filtrar();

  filas.innerHTML = lista.map(e=>{
    const clases = [e.estado==='descartado' ? 'descartado' : '', esValidado(e.id) ? 'validado' : '']
      .filter(Boolean).join(' ');
    const boton = tieneCoords(e)
      ? `<button class="btn-mapa" type="button" data-id="${esc(e.id)}">Ver</button>`
      : '<span class="sin-coords" title="Sin coordenadas">-</span>';
    const casilla = `<input type="checkbox" class="chk-validar" data-validar-id="${esc(e.id)}"` +
      (esValidado(e.id) ? ' checked' : '') +
      ` aria-label="Validar evento ${esc(e.evento)}">`;
    const fuentesEvento = e.fuentes || [];
    const soloRed = fuentesEvento.length > 0 && fuentesEvento.every(f=>esRedSocial(f.url));
    const avisos =
      (tieneCoords(e) ? '' : '<span class="badge badge-aviso" title="Sin coordenadas: no aparece en el mapa">sin coords</span>') +
      (soloRed ? '<span class="badge badge-red" title="Todas sus fuentes son redes sociales; verificar en el medio">solo red</span>' : '');
    return `<tr${clases ? ' class="' + clases + '"' : ''}>
      <td>${esc(fechaCorta(e.fecha_publicacion||e.fecha_deteccion))}</td>
      <td><span class="tipo" style="background:${colorTipo(e.tipo_evento)}">${esc(etiquetaTipo(e.tipo_evento))}</span></td>
      <td class="evento">${esc(e.evento)}${avisos}</td>
      <td>${esc(e.region||'-')}${e.comuna?' / '+esc(e.comuna):''}</td>
      <td>${detallesFuentes(e.fuentes)}</td>
      <td class="estado-${esc(e.estado||'nuevo')}">${esc(e.estado||'nuevo')}</td>
      <td class="col-mapa">${boton}</td>
      <td class="col-validar">${casilla}</td>
    </tr>`;
  }).join('');
  document.getElementById('vacio').style.display = lista.length ? 'none' : 'block';

  capa.clearLayers();
  marcadores.clear();
  lista.filter(e=>tieneCoords(e) && e.estado!=='descartado').forEach(e=>{
    const m = L.circleMarker([parseFloat(e.lat), parseFloat(e.lon)],{
      radius:7, color:'#fff', weight:1.5, fillColor:colorTipo(e.tipo_evento), fillOpacity:.9
    });
    const links = (e.fuentes||[]).map(f=> f.url
      ? `<a href="${esc(f.url)}" target="_blank" rel="noopener">${esc(f.medio||'Fuente')}</a>`
      : esc(f.medio||'Fuente')
    ).join('<br>');
    m.bindPopup(`<b>${esc(e.evento)}</b><br>${esc(fechaCorta(e.fecha_publicacion||e.fecha_deteccion))}<br>${esc(e.region||'')} ${esc(e.comuna||'')}<br><br>${links}`);
    m.addTo(capa);
    marcadores.set(String(e.id), m);
  });

  const porTipo = {};
  lista.filter(e=>e.estado!=='descartado').forEach(e=>{
    const t = e.tipo_evento || 'otro';
    porTipo[t] = (porTipo[t]||0)+1;
  });
  const hace7 = EVENTOS.filter(e=>e.estado!=='descartado' && dentroDeRango(e,7)).length;
  document.getElementById('resumen').innerHTML =
    `<div class="tarjeta"><b>${lista.length}</b><span>En el filtro</span></div>` +
    `<div class="tarjeta"><b>${hace7}</b><span>Ultimos 7 dias</span></div>` +
    Object.keys(porTipo).sort().map(t=>`<div class="tarjeta"><b>${porTipo[t]}</b><span>${esc(etiquetaTipo(t))}</span></div>`).join('');

  document.getElementById('contador').textContent = `${lista.length} de ${EVENTOS.length} eventos`;
  return lista;
}

function limpiar(){
  buscar.value = '';
  selTipo.value = '';
  selRegion.value = '';
  inputPeriodo.value = 90;
  soloValidados = false;
  btnValidados.classList.remove('activo');
  btnValidados.setAttribute('aria-pressed', 'false');
  poblarComunas();
  render();
}

// ---- descarga de eventos validados (CSV generado en el navegador) ----
function avisar(msg, ms){
  cajaEstado.textContent = msg;
  cajaEstado.classList.add('visible');
  if (ms) setTimeout(()=>cajaEstado.classList.remove('visible'), ms);
}

// Separa el CSV en registros respetando comillas y saltos de linea dentro de campos.
function registrosCsv(texto){
  const salida = []; let actual = ''; let entreComillas = false;
  for (let i=0;i<texto.length;i++){
    const c = texto[i];
    if (entreComillas){
      actual += c;
      if (c === '"'){
        if (texto[i+1] === '"'){ actual += texto[++i]; } else { entreComillas = false; }
      }
    } else if (c === '"'){ entreComillas = true; actual += c; }
    else if (c === '\\n'){ salida.push(actual); actual = ''; }
    else if (c !== '\\r'){ actual += c; }
  }
  if (actual) salida.push(actual);
  return salida.filter(l=>l.trim().length);
}

function primeraCelda(registro){
  const i = registro.indexOf(',');
  return i < 0 ? registro : registro.slice(0, i);
}

async function descargarValidados(){
  const ids = new Set(Object.keys(VALIDADOS).filter(k=>VALIDADOS[k]));
  if (!ids.size){ avisar('Marca al menos un evento como validado para descargar.', 6000); return; }
  const textoPrevio = btnDescargar.textContent;
  btnDescargar.disabled = true;
  btnDescargar.textContent = 'Preparando...';
  try {
    const resp = await fetch('eventos.csv?t=' + Date.now(), {cache:'no-store'});
    if (!resp.ok) throw new Error('no se pudo leer eventos.csv');
    const texto = await resp.text();
    const registros = registrosCsv(texto);
    if (!registros.length) throw new Error('eventos.csv esta vacio');
    const cabecera = registros.shift();
    const elegidos = registros.filter(r=>ids.has(primeraCelda(r)));
    if (!elegidos.length) throw new Error('los eventos validados no estan en el CSV publicado');
    const bom = texto.charCodeAt(0) === 0xFEFF ? '' : '\\uFEFF';
    const contenido = bom + [cabecera, ...elegidos].join('\\r\\n') + '\\r\\n';
    const hoy = new Date().toISOString().slice(0,10);
    const url = URL.createObjectURL(new Blob([contenido], {type:'text/csv;charset=utf-8'}));
    const enlace = document.createElement('a');
    enlace.href = url;
    enlace.download = `eventos_validados_${hoy}.csv`;
    document.body.appendChild(enlace);
    enlace.click();
    enlace.remove();
    setTimeout(()=>URL.revokeObjectURL(url), 2000);
    avisar(`Descargados ${elegidos.length} evento${elegidos.length===1?'':'s'} validado${elegidos.length===1?'':'s'}.`, 7000);
  } catch (err) {
    avisar('Error al descargar: ' + err.message, 8000);
  } finally {
    btnDescargar.textContent = textoPrevio;
    refrescarBotonDescarga();
  }
}

async function actualizar(){
  btnActualizar.disabled = true;
  btnActualizar.textContent = 'Actualizando...';
  cajaEstado.textContent = ES_LOCAL ? 'Buscando nuevas remociones...' : 'Descargando la ultima version...';
  cajaEstado.classList.add('visible');
  try {
    if (ES_LOCAL){
      const resp = await fetch('/actualizar', {method:'POST'});
      const res = await resp.json().catch(()=>({ok:false, mensaje:'respuesta invalida'}));
      if (!resp.ok || !res.ok) throw new Error(res.mensaje || 'fallo la busqueda');
    }
    const resp = await fetch('eventos.json?t=' + Date.now(), {cache:'no-store'});
    if (!resp.ok) throw new Error('no se pudo leer eventos.json');
    const datos = await resp.json();
    EVENTOS = Array.isArray(datos) ? datos : (datos.eventos || []);
    ACTUALIZADO = (datos && datos.actualizado) || ACTUALIZADO;
    document.getElementById('actualizado').textContent = ACTUALIZADO;
    poblarFiltros();
    const encontrados = render();
    const ajustado = ajustarMapaALista(encontrados);
    cajaEstado.textContent = 'Actualizado: ' + new Date().toLocaleTimeString('es-CL',{hour:'2-digit',minute:'2-digit'}) +
      ` - ${encontrados.length} evento${encontrados.length===1?'':'s'} en el filtro` +
      (ajustado ? '' : ' (sin coordenadas para encuadrar)');
    setTimeout(()=>cajaEstado.classList.remove('visible'), 6000);
  } catch (err) {
    if (ES_LOCAL){
      cajaEstado.textContent = 'Error: ' + err.message;
    } else {
      cajaEstado.textContent = 'Recargando la pagina...';
      location.reload();
      return;
    }
  } finally {
    btnActualizar.disabled = false;
    btnActualizar.textContent = 'Actualizar';
  }
}

filas.addEventListener('click', ev=>{
  if (ev.target.closest('input')) return;  // la casilla no debe centrar el mapa
  const id = ev.target.getAttribute('data-id');
  if (id) enfocar(id);
});

filas.addEventListener('change', ev=>{
  const casilla = ev.target.closest('.chk-validar');
  if (!casilla) return;
  marcarValidado(casilla.getAttribute('data-validar-id'), casilla.checked);
  const fila = casilla.closest('tr');
  if (fila) fila.classList.toggle('validado', casilla.checked);
  if (soloValidados) render();  // con el filtro activo, la fila entra o sale al instante
});

selRegion.addEventListener('change', ()=>{ poblarComunas(); render(); });
[selTipo, selComuna].forEach(s=>s.addEventListener('change', render));
inputPeriodo.addEventListener('input', render);
buscar.addEventListener('input', render);
document.getElementById('btn-limpiar').addEventListener('click', limpiar);
btnValidados.addEventListener('click', ()=>{
  soloValidados = !soloValidados;
  btnValidados.classList.toggle('activo', soloValidados);
  btnValidados.setAttribute('aria-pressed', soloValidados ? 'true' : 'false');
  render();
});
btnActualizar.addEventListener('click', actualizar);

poblarFiltros();
render();
refrescarBotonDescarga();
</script>
</body>
</html>
"""


def _actualizado(eventos: list[dict]) -> str:
    """Fecha de la ultima deteccion (estable si no hay eventos nuevos)."""
    fechas = []
    for evento in eventos:
        valor = evento.get("fecha_deteccion")
        if not valor:
            continue
        try:
            fechas.append(datetime.fromisoformat(valor))
        except ValueError:
            continue
    if not fechas:
        return ahora().strftime("%Y-%m-%d %H:%M")
    return max(fechas).astimezone(ahora().tzinfo).strftime("%Y-%m-%d %H:%M")


def _datos_para_sitio(eventos: list[dict]) -> list[dict]:
    salida = []
    for e in eventos:
        salida.append(
            {
                "id": e.get("id", ""),
                "fecha_publicacion": e.get("fecha_publicacion", ""),
                "fecha_deteccion": e.get("fecha_deteccion", ""),
                "titulo": e.get("titulo", ""),
                "evento": etiqueta_evento(e),
                "tipo_evento": e.get("tipo_evento", ""),
                "tipo_etiqueta": e.get("tipo_etiqueta", ""),
                "region": e.get("region", ""),
                "comuna": e.get("comuna", ""),
                "lat": e.get("lat", ""),
                "lon": e.get("lon", ""),
                "fuentes": fuentes(e),
                "estado": e.get("estado", "nuevo"),
            }
        )
    return salida


def generar_sitio(eventos: list[dict] | None = None, config: dict | None = None) -> Path:
    """Genera docs/index.html, docs/eventos.json y docs/eventos.csv."""
    eventos = cargar_eventos() if eventos is None else eventos
    eventos = ordenar_eventos(eventos)  # mismo orden que data/eventos.csv
    config = config or {}
    DOCS.mkdir(parents=True, exist_ok=True)

    tipos = {}
    for tipo, defn in (config.get("tipos_evento") or {}).items():
        tipos[tipo] = defn.get("etiqueta", tipo)

    regiones = []
    for entrada in (config.get("geografia") or {}).get("regiones", []):
        regiones.append(entrada if isinstance(entrada, str) else entrada.get("nombre", ""))

    actualizado = _actualizado(eventos)

    datos = _datos_para_sitio(eventos)
    datos_json = json.dumps(datos, ensure_ascii=False).replace("</", "<\\/")

    html_final = (
        PLANTILLA.replace("__ACTUALIZADO__", actualizado)
        .replace("__DATOS__", datos_json)
        .replace("__TIPOS__", json.dumps(tipos, ensure_ascii=False))
        .replace("__REGIONES__", json.dumps(regiones, ensure_ascii=False))
        .replace("__COLORES__", json.dumps(COLORES, ensure_ascii=False))
    )
    destino = DOCS / "index.html"
    destino.write_text(html_final, encoding="utf-8")

    (DOCS / "eventos.json").write_text(
        json.dumps(
            {"actualizado": actualizado, "total": len(datos), "eventos": datos},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    if CSV.exists():
        shutil.copyfile(CSV, DOCS / "eventos.csv")

    return destino
