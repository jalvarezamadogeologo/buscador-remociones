"""Servidor local del catastro.

Sirve `docs/` en 127.0.0.1 y expone dos endpoints de escritura:

- `POST /actualizar`: ejecuta la busqueda real (actualizar.py) y devuelve el resultado.
- `POST /estado`: cambia el estado de revision de un evento (`nuevo`, `confirmado` o
  `descartado`) en `data/eventos.csv` y regenera el sitio. Es la unica forma de que
  el sitio escriba el estado: GitHub Pages es estatico y no puede modificar el repo.

Uso:
    python servidor.py                 # abre el navegador en 127.0.0.1:8770
    python servidor.py --lookback 48
    python servidor.py --puerto 9000 --no-abrir
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import threading
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from comun import cargar_config
from estado import aplicar_estado
from generar_sitio import generar_sitio
from guardar import cargar_eventos, guardar_eventos

RAIZ = Path(__file__).resolve().parent
DOCS = RAIZ / "docs"
LOOKBACK = 24
MAX_CUERPO = 4096
# Serializa las escrituras: ThreadingHTTPServer atiende peticiones en paralelo.
CANDADO = threading.Lock()


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DOCS), **kwargs)

    def _responder(self, codigo: int, datos: dict) -> None:
        cuerpo = json.dumps(datos, ensure_ascii=False).encode("utf-8")
        self.send_response(codigo)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(cuerpo)))
        self.end_headers()
        self.wfile.write(cuerpo)

    def do_POST(self):  # noqa: N802 (nombre impuesto por http.server)
        if not self._origen_permitido():
            self.send_error(403, "Origen no permitido")
            return
        ruta = urlparse(self.path).path
        if ruta == "/actualizar":
            self._actualizar()
        elif ruta == "/estado":
            self._cambiar_estado()
        else:
            self.send_error(404, "Ruta no encontrada")

    def _origen_permitido(self) -> bool:
        """Bloquea POST de otras webs al servidor local (CSRF).

        Los scripts locales (curl, tests) no mandan Origin y se aceptan. El navegador
        si lo manda en un POST: solo se permite el propio servidor en 127.0.0.1/localhost.
        """
        origen = (self.headers.get("Origin") or "").strip()
        if not origen:
            return True
        puerto = getattr(self.server, "server_port", 0)
        return origen in {f"http://127.0.0.1:{puerto}", f"http://localhost:{puerto}"}

    def _actualizar(self) -> None:
        try:
            cmd = [
                sys.executable,
                str(RAIZ / "actualizar.py"),
                "--lookback",
                str(LOOKBACK),
                "--sin-notificar",
            ]
            proc = subprocess.run(cmd, cwd=str(RAIZ), capture_output=True, text=True, timeout=600)
            ok = proc.returncode == 0
            self._responder(
                200 if ok else 500,
                {
                    "ok": ok,
                    "mensaje": "Actualizacion completada" if ok else "La busqueda fallo",
                    "salida": ((proc.stdout or "") + (proc.stderr or ""))[-3000:],
                },
            )
        except subprocess.TimeoutExpired:
            self._responder(500, {"ok": False, "mensaje": "La busqueda excedio 10 minutos"})
        except Exception as exc:  # servidor local: informar sin caerse
            self._responder(500, {"ok": False, "mensaje": f"Error: {exc}"})

    def _cambiar_estado(self) -> None:
        try:
            largo = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            largo = 0
        if largo <= 0 or largo > MAX_CUERPO:
            self._responder(400, {"ok": False, "mensaje": "cuerpo invalido"})
            return
        try:
            datos = json.loads(self.rfile.read(largo).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._responder(400, {"ok": False, "mensaje": "JSON invalido"})
            return
        if not isinstance(datos, dict):
            self._responder(400, {"ok": False, "mensaje": "se esperaba un objeto JSON"})
            return

        id_evento = str(datos.get("id") or "")
        estado = str(datos.get("estado") or "")
        with CANDADO:
            eventos = cargar_eventos()
            try:
                evento = aplicar_estado(eventos, id_evento, estado)
            except ValueError as exc:
                self._responder(400, {"ok": False, "mensaje": str(exc)})
                return
            except KeyError:
                self._responder(
                    404, {"ok": False, "mensaje": f"evento no encontrado: {id_evento}"}
                )
                return

            guardar_eventos(eventos)
            try:
                generar_sitio(eventos, cargar_config())
            except Exception as exc:
                self._responder(
                    500,
                    {"ok": False, "mensaje": f"estado guardado, pero fallo el sitio: {exc}"},
                )
                return

        self._responder(
            200,
            {
                "ok": True,
                "mensaje": f"estado cambiado a {evento['estado']}",
                "id": evento.get("id"),
                "estado": evento.get("estado"),
            },
        )

    def log_message(self, format, *args):  # noqa: A002 (firma de la clase base)
        print(f"[servidor] {format % args}", flush=True)


def main() -> int:
    global LOOKBACK
    parser = argparse.ArgumentParser(description="Servidor local del catastro de remociones")
    parser.add_argument("--puerto", type=int, default=8770)
    parser.add_argument("--lookback", type=int, default=24, help="horas hacia atras al actualizar")
    parser.add_argument("--no-abrir", action="store_true", help="no abrir el navegador")
    args = parser.parse_args()

    LOOKBACK = args.lookback
    if not DOCS.exists():
        print("[servidor] falta docs/. Ejecuta antes: python actualizar.py --sin-notificar")
        return 1

    servidor = ThreadingHTTPServer(("127.0.0.1", args.puerto), Handler)
    url = f"http://127.0.0.1:{args.puerto}/"
    print(f"[servidor] {url} (Ctrl+C para detener)", flush=True)
    if not args.no_abrir:
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()

    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\n[servidor] detenido")
    finally:
        servidor.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
