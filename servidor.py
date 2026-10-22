"""Servidor local del catastro.

Sirve `docs/` en 127.0.0.1 y expone `POST /actualizar`, que ejecuta la busqueda
real (actualizar.py) y devuelve el resultado. El boton "Actualizar" del sitio
detecta que corre en localhost y llama a este endpoint.

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

RAIZ = Path(__file__).resolve().parent
DOCS = RAIZ / "docs"
LOOKBACK = 24


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DOCS), **kwargs)

    def do_POST(self):  # noqa: N802 (nombre impuesto por http.server)
        if urlparse(self.path).path != "/actualizar":
            self.send_error(404, "Ruta no encontrada")
            return

        codigo = 200
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
            cuerpo = json.dumps(
                {
                    "ok": ok,
                    "mensaje": "Actualizacion completada" if ok else "La busqueda fallo",
                    "salida": ((proc.stdout or "") + (proc.stderr or ""))[-3000:],
                },
                ensure_ascii=False,
            ).encode("utf-8")
            if not ok:
                codigo = 500
        except subprocess.TimeoutExpired:
            codigo = 500
            cuerpo = json.dumps(
                {"ok": False, "mensaje": "La busqueda excedio 10 minutos"}, ensure_ascii=False
            ).encode("utf-8")
        except Exception as exc:  # servidor local: informar sin caerse
            codigo = 500
            cuerpo = json.dumps({"ok": False, "mensaje": f"Error: {exc}"}, ensure_ascii=False).encode(
                "utf-8"
            )

        self.send_response(codigo)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(cuerpo)))
        self.end_headers()
        self.wfile.write(cuerpo)

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
