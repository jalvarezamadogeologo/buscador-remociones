"""Notificacion de eventos nuevos como GitHub Issues.

Requiere GITHUB_TOKEN (o GH_TOKEN) con permisos contents/issues. En local,
sin token, funciona en modo simulado (no crea nada).
"""

from __future__ import annotations

import os
import re

import requests

from comun import log

API = "https://api.github.com"
VERSION = "2022-11-28"


def _headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": VERSION,
    }


def _repo(config: dict) -> str:
    return os.environ.get("GITHUB_REPOSITORY") or (config.get("repo") or "")


def _token() -> str:
    return os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or ""


def asegurar_etiqueta(repo: str, token: str, etiqueta: str) -> None:
    url = f"{API}/repos/{repo}/labels"
    payload = {
        "name": etiqueta,
        "color": "b60205",
        "description": "Eventos de remocion en masa detectados automaticamente",
    }
    try:
        resp = requests.post(url, json=payload, headers=_headers(token), timeout=20)
        if resp.status_code not in (201, 422):  # 422 = ya existe
            log(f"aviso: no se pudo crear la etiqueta {etiqueta} ({resp.status_code})")
    except requests.RequestException as exc:
        log(f"aviso: fallo al crear la etiqueta {etiqueta}: {exc}")


def urls_notificadas(repo: str, token: str, etiqueta: str) -> set[str]:
    """URLs ya presentes en issues recientes con la etiqueta (evita duplicados)."""
    url = f"{API}/repos/{repo}/issues"
    params = {"labels": etiqueta, "state": "all", "per_page": 100, "sort": "created", "direction": "desc"}
    try:
        resp = requests.get(url, params=params, headers=_headers(token), timeout=25)
        resp.raise_for_status()
        urls: set[str] = set()
        for issue in resp.json():
            cuerpo = issue.get("body") or ""
            urls.update(re.findall(r"https?://[^\s)\]>]+", cuerpo))
        return urls
    except requests.RequestException as exc:
        log(f"aviso: no se pudieron listar issues existentes: {exc}")
        return set()


def _cuerpo(evento: dict) -> str:
    url = evento.get("url", "")
    lineas = [
        f"**Tipo:** {evento.get('tipo_etiqueta') or evento.get('tipo_evento')}",
        f"**Fecha de publicacion:** {evento.get('fecha_publicacion') or 'sin fecha'}",
        f"**Region / comuna:** {evento.get('region') or '-'} / {evento.get('comuna') or '-'}",
        f"**Fuente:** {evento.get('fuente') or '-'}",
        f"**Detectado:** {evento.get('fecha_deteccion')}",
        f"**Keywords:** {evento.get('keywords')}",
        "",
        evento.get("descripcion") or "(sin descripcion)",
        "",
    ]
    if url:
        lineas.append(f"[Ver noticia]({url})")
    lineas += [
        "",
        "---",
        "Generado automaticamente por catastro-remociones.",
        "Para confirmar o descartar, edita `data/eventos.csv` (columna `estado`).",
    ]
    return "\n".join(lineas)


def crear_issue(repo: str, token: str, etiqueta: str, evento: dict) -> int | None:
    titulo = f"[Remocion] {evento.get('tipo_etiqueta') or 'Evento'}: {evento.get('titulo', '')}"
    titulo = titulo[:250]
    payload = {"title": titulo, "body": _cuerpo(evento), "labels": [etiqueta]}
    try:
        resp = requests.post(
            f"{API}/repos/{repo}/issues", json=payload, headers=_headers(token), timeout=25
        )
        if resp.status_code == 201:
            return int(resp.json()["number"])
        log(f"aviso: issue no creado ({resp.status_code}): {resp.text[:200]}")
    except (requests.RequestException, ValueError, KeyError) as exc:
        log(f"aviso: fallo al crear issue: {exc}")
    return None


def notificar(eventos: list[dict], config: dict, solo_ids: set[str] | None = None) -> int:
    """Crea issues para eventos nuevos pendientes. Devuelve cuantos se crearon.

    `solo_ids` limita la notificacion a los eventos detectados en la corrida
    actual; sin el, se notificarian tambien los eventos historicos del catastro.
    """
    repo = _repo(config)
    token = _token()
    etiqueta = config.get("etiqueta_issue", "remocion-en-masa")
    if not repo or not token:
        log("notificacion omitida: sin GITHUB_REPOSITORY/GITHUB_TOKEN (modo local)")
        return 0

    maximo = int(config.get("max_notificaciones", 20))
    pendientes = [
        e
        for e in eventos
        if e.get("estado") == "nuevo"
        and not e.get("issue")
        and (solo_ids is None or e.get("id") in solo_ids)
    ]
    if not pendientes:
        return 0
    if maximo:
        pendientes = pendientes[:maximo]

    asegurar_etiqueta(repo, token, etiqueta)
    ya_notificadas = urls_notificadas(repo, token, etiqueta)

    creados = 0
    for evento in pendientes:
        url = evento.get("url", "")
        if url and url in ya_notificadas:
            log(f"  issue ya existente para: {evento.get('titulo', '')[:70]}")
            continue
        numero = crear_issue(repo, token, etiqueta, evento)
        if numero:
            evento["issue"] = str(numero)
            ya_notificadas.add(url)
            creados += 1
            log(f"  issue #{numero}: {evento.get('titulo', '')[:70]}")
    return creados
