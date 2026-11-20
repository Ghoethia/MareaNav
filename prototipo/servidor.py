"""Servidor local del prototipo. Uso: python -m prototipo.servidor"""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from prototipo.benchmark import ESCENARIOS, topologia
from prototipo.estrategias import catalogo
from prototipo.patrones import NavegadorMareas
from prototipo.terminal import construir_demostracion

WEB = Path(__file__).resolve().parent / "web"
SESION: dict = {"navegador": None, "id": None}


def _escenario(identificador: str) -> dict:
    for escenario in ESCENARIOS:
        if escenario["id"] == identificador:
            return escenario
    raise KeyError(identificador)


def _comparar(escenario: dict) -> dict:
    grafo, terminal, origen, destino = construir_demostracion(escenario["congestion"])
    filas = []
    for estrategia in catalogo().values():
        plan = estrategia.calcular(grafo, terminal, origen, destino, escenario["marea_alta"])
        datos = plan.a_dict()
        datos["itinerario"] = [grafo.nodos[nodo].nombre for nodo in plan.camino]
        filas.append(datos)
    navegador = NavegadorMareas.crear(
        grafo, terminal, escenario["congestion"], escenario["marea_alta"]
    )
    return {
        "escenario": {
            "id": escenario["id"],
            "titulo": escenario["titulo"],
            "congestion_arteria": escenario["congestion"],
            "marea_alta": escenario["marea_alta"],
        },
        "topologia": topologia(escenario["congestion"]),
        "resultados": filas,
        "politica": {
            "estrategia": navegador.contexto.estrategia.nombre,
            "motivo": navegador.planificador.motivo,
        },
        "origen": origen,
        "destino": destino,
    }


class Manejador(BaseHTTPRequestHandler):
    def _json(self, carga: dict, estado: int = 200) -> None:
        cuerpo = json.dumps(carga, ensure_ascii=False).encode("utf-8")
        self.send_response(estado)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(cuerpo)))
        self.end_headers()
        self.wfile.write(cuerpo)

    def _leer(self) -> dict:
        longitud = int(self.headers.get("Content-Length", "0"))
        if longitud <= 0:
            return {}
        return json.loads(self.rfile.read(longitud).decode("utf-8"))

    def _archivo(self, ruta: str) -> None:
        relativo = "index.html" if ruta in ("", "/") else ruta.lstrip("/")
        destino = (WEB / relativo).resolve()
        if WEB.resolve() not in destino.parents and destino != WEB.resolve():
            self.send_error(403)
            return
        if not destino.is_file():
            self.send_error(404)
            return
        tipos = {
            ".html": "text/html; charset=utf-8",
            ".css": "text/css; charset=utf-8",
            ".js": "text/javascript; charset=utf-8",
            ".svg": "image/svg+xml",
        }
        contenido = destino.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", tipos.get(destino.suffix, "application/octet-stream"))
        self.send_header("Content-Length", str(len(contenido)))
        self.end_headers()
        self.wfile.write(contenido)

    def do_GET(self) -> None:  # noqa: N802
        ruta = urlparse(self.path).path
        if ruta == "/api/escenarios":
            self._json({"escenarios": list(ESCENARIOS)})
            return
        if ruta.startswith("/api/"):
            self._json({"error": "Ruta no disponible"}, 404)
            return
        self._archivo(ruta)

    def do_POST(self) -> None:  # noqa: N802
        ruta = urlparse(self.path).path
        try:
            cuerpo = self._leer()
            if ruta == "/api/comparar":
                self._json(_comparar(_escenario(cuerpo["id"])))
                return
            if ruta == "/api/calcular":
                escenario = _escenario(cuerpo["id"])
                if SESION.get("id") != escenario["id"] or SESION.get("navegador") is None:
                    grafo, terminal, _, _ = construir_demostracion(escenario["congestion"])
                    SESION["navegador"] = NavegadorMareas.crear(
                        grafo, terminal, escenario["congestion"], escenario["marea_alta"]
                    )
                    SESION["id"] = escenario["id"]
                navegador = SESION["navegador"]
                if cuerpo.get("estrategia"):
                    navegador.contexto.fijar(catalogo()[cuerpo["estrategia"]])
                plan = navegador.calcular("PO", "MU")
                self._json(
                    {
                        "plan": plan.a_dict(),
                        "itinerario": navegador.itinerario(plan),
                        "politica": {
                            "estrategia": navegador.contexto.estrategia.nombre,
                            "motivo": navegador.planificador.motivo,
                        },
                        "bitacora": [registro.__dict__ for registro in navegador.invocador.bitacora()],
                    }
                )
                return
            if ruta == "/api/deshacer":
                navegador = SESION.get("navegador")
                if navegador is None:
                    self._json({"ok": False, "mensaje": "No hay despachos registrados"}, 400)
                    return
                ok = navegador.deshacer()
                plan = navegador.plan_vigente
                self._json(
                    {
                        "ok": ok,
                        "plan": plan.a_dict() if plan else None,
                        "itinerario": navegador.itinerario(plan) if plan else [],
                        "bitacora": [registro.__dict__ for registro in navegador.invocador.bitacora()],
                    }
                )
                return
            self._json({"error": "Ruta no disponible"}, 404)
        except KeyError:
            self._json({"error": "Escenario desconocido"}, 400)
        except Exception as exc:  # noqa: BLE001
            self._json({"error": str(exc)}, 500)

    def log_message(self, formato: str, *args) -> None:
        print("[MareaNav]", self.address_string(), formato % args)


def main() -> None:
    servidor = ThreadingHTTPServer(("127.0.0.1", 8765), Manejador)
    print("MareaNav en http://127.0.0.1:8765")
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        servidor.shutdown()


if __name__ == "__main__":
    main()
