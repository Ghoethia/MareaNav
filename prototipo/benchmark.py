"""Ejecución de escenarios, política reactiva y crecimiento de la búsqueda."""

from __future__ import annotations

import json
import statistics
from pathlib import Path

from prototipo.estrategias import catalogo
from prototipo.patrones import NavegadorMareas
from prototipo.terminal import construir_demostracion, construir_escala

RAIZ = Path(__file__).resolve().parents[1]
SALIDA = RAIZ / "resultados"

ESCENARIOS = (
    {
        "id": "estable",
        "titulo": "Marea alta y congestión baja",
        "congestion": 0.10,
        "marea_alta": True,
    },
    {
        "id": "congestion",
        "titulo": "Marea alta y congestión alta",
        "congestion": 0.85,
        "marea_alta": True,
    },
    {
        "id": "marea",
        "titulo": "Marea baja",
        "congestion": 0.20,
        "marea_alta": False,
    },
)


def _median_ms(estrategia, grafo, terminal, origen, destino, marea_alta, repeticiones=21) -> float:
    tiempos = []
    for _ in range(repeticiones):
        plan = estrategia.calcular(grafo, terminal, origen, destino, marea_alta)
        tiempos.append(plan.tiempo_calculo_ms)
    return statistics.median(tiempos)


def evaluar_escenario(escenario: dict) -> dict:
    grafo, terminal, origen, destino = construir_demostracion(escenario["congestion"])
    marea = escenario["marea_alta"]
    resultados = []
    for estrategia in catalogo().values():
        plan = estrategia.calcular(grafo, terminal, origen, destino, marea)
        datos = plan.a_dict()
        datos["tiempo_calculo_ms"] = round(
            _median_ms(estrategia, grafo, terminal, origen, destino, marea),
            4,
        )
        datos["itinerario"] = [
            grafo.nodos[nodo].nombre for nodo in plan.camino
        ]
        resultados.append(datos)

    navegador = NavegadorMareas.crear(grafo, terminal, escenario["congestion"], marea)
    plan_politica = navegador.calcular(origen, destino)
    return {
        "id": escenario["id"],
        "titulo": escenario["titulo"],
        "congestion_arteria": escenario["congestion"],
        "marea_alta": marea,
        "origen": origen,
        "destino": destino,
        "nodos": len(grafo.nodos),
        "resultados": resultados,
        "politica": {
            "estrategia": navegador.contexto.estrategia.nombre,
            "motivo": navegador.planificador.motivo,
            "costo_real_s": round(plan_politica.costo_real_s, 3),
            "nodos_expandidos": plan_politica.nodos_expandidos,
            "camino": plan_politica.camino,
        },
    }


def evaluar_escala() -> list[dict]:
    filas = []
    for lado in (6, 10, 16, 24):
        grafo, terminal, origen, destino = construir_escala(lado)
        entrada = {
            "lado": lado,
            "nodos": len(grafo.nodos),
            "aristas_dirigidas": sum(len(v) for v in grafo.adyacencia.values()),
            "estrategias": [],
        }
        for nombre in ("Dijkstra", "A*", "Jerárquica"):
            estrategia = catalogo()[nombre]
            plan = estrategia.calcular(grafo, terminal, origen, destino, True)
            entrada["estrategias"].append(
                {
                    "estrategia": nombre,
                    "costo_real_s": round(plan.costo_real_s, 3),
                    "nodos_expandidos": plan.nodos_expandidos,
                    "tiempo_calculo_ms": round(
                        _median_ms(estrategia, grafo, terminal, origen, destino, True, 11),
                        4,
                    ),
                    "exito": plan.exito,
                    "distancia_m": round(plan.distancia_m, 1),
                }
            )
        filas.append(entrada)
    return filas


def demostrar_patrones() -> dict:
    grafo, terminal, origen, destino = construir_demostracion(0.85)
    navegador = NavegadorMareas.crear(grafo, terminal, 0.85, True)
    primero = navegador.calcular(origen, destino)
    navegador.monitor.fijar(0.10, True)
    segundo = navegador.calcular(origen, destino)
    deshecho = navegador.deshacer()
    restaurado = navegador.plan_vigente
    itinerario = navegador.itinerario(primero)
    return {
        "comandos_en_bitacora": len(navegador.invocador.bitacora()),
        "deshacer_exitoso": deshecho,
        "estrategia_congestion": primero.estrategia,
        "estrategia_estable": segundo.estrategia,
        "camino_restaurado": restaurado.camino if restaurado else [],
        "coincide_con_primero": restaurado is not None and restaurado.camino == primero.camino,
        "paradas_iterador": len(itinerario),
        "itinerario": itinerario,
        "nodos_composite": len(terminal.nodos()),
        "nodos_grafo": len(grafo.nodos),
        "zonas_no_transitables": [
            hoja.nombre() for hoja in terminal.hojas() if not hoja.transitable
        ],
    }


def topologia(congestion: float = 0.85) -> dict:
    grafo, terminal, origen, destino = construir_demostracion(congestion)
    nodos = [
        {
            "id": nodo.id,
            "nombre": nodo.nombre,
            "x": nodo.x,
            "y": nodo.y,
            "zona": nodo.zona,
        }
        for nodo in grafo.nodos.values()
    ]
    aristas = []
    vistas: set[tuple[str, str]] = set()
    for lista in grafo.adyacencia.values():
        for arista in lista:
            clave = tuple(sorted((arista.origen, arista.destino)))
            if clave in vistas:
                continue
            vistas.add(clave)
            aristas.append(
                {
                    "origen": arista.origen,
                    "destino": arista.destino,
                    "distancia": round(arista.distancia, 1),
                    "congestion": arista.congestion,
                    "requiere_marea_alta": arista.requiere_marea_alta,
                }
            )
    return {
        "nodos": nodos,
        "aristas": aristas,
        "origen": origen,
        "destino": destino,
        "zonas": [
            {"nombre": hoja.nombre(), "transitable": hoja.transitable, "nodos": [n.id for n in hoja.nodos()]}
            for hoja in terminal.hojas()
        ],
    }


def ejecutar() -> dict:
    return {
        "escenarios": [evaluar_escenario(escenario) for escenario in ESCENARIOS],
        "escalabilidad": evaluar_escala(),
        "patrones": demostrar_patrones(),
    }


def guardar(metricas: dict | None = None) -> Path:
    SALIDA.mkdir(parents=True, exist_ok=True)
    datos = metricas or ejecutar()
    destino = SALIDA / "metricas.json"
    destino.write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")
    return destino


if __name__ == "__main__":
    ruta = guardar()
    print(ruta)
