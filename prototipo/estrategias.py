"""Patrón Strategy: algoritmos intercambiables de navegación."""

from __future__ import annotations

import heapq
import math
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass

from prototipo.modelo import (
    VELOCIDAD_MS,
    GrafoTerminal,
    ZonaCompuesta,
    costo_distancia,
    costo_tiempo,
)


@dataclass
class PlanRuta:
    estrategia: str
    camino: list[str]
    costo_real_s: float
    distancia_m: float
    nodos_expandidos: int
    tiempo_calculo_ms: float
    exito: bool

    def a_dict(self) -> dict:
        return {
            "estrategia": self.estrategia,
            "camino": self.camino,
            "costo_real_s": round(self.costo_real_s, 3),
            "distancia_m": round(self.distancia_m, 1),
            "nodos_expandidos": self.nodos_expandidos,
            "tiempo_calculo_ms": round(self.tiempo_calculo_ms, 4),
            "exito": self.exito,
            "saltos": max(0, len(self.camino) - 1),
        }


def _reconstruir(padre: dict[str, str | None], destino: str) -> list[str]:
    camino: list[str] = []
    actual: str | None = destino
    while actual is not None:
        camino.append(actual)
        actual = padre.get(actual)
    camino.reverse()
    return camino


def _evaluar(grafo: GrafoTerminal, camino: list[str], marea_alta: bool) -> tuple[float, float]:
    tiempo = 0.0
    distancia = 0.0
    for origen, destino in zip(camino, camino[1:]):
        arista = grafo.arista(origen, destino)
        tiempo += costo_tiempo(arista, marea_alta)
        distancia += arista.distancia
    return tiempo, distancia


def buscar(
    grafo: GrafoTerminal,
    origen: str,
    destino: str,
    marea_alta: bool,
    usar_tiempo: bool,
    usar_heuristica: bool,
    permitidos: set[str] | None = None,
) -> tuple[list[str] | None, int]:
    """Búsqueda de costo uniforme o A*, con poda opcional de nodos."""

    def costo(arista):
        if usar_tiempo:
            return costo_tiempo(arista, marea_alta)
        return costo_distancia(arista, marea_alta)

    def heuristica(nodo_id: str) -> float:
        if not usar_heuristica:
            return 0.0
        actual = grafo.nodos[nodo_id]
        meta = grafo.nodos[destino]
        euclidea = math.hypot(actual.x - meta.x, actual.y - meta.y)
        if usar_tiempo:
            return euclidea / VELOCIDAD_MS
        return euclidea

    frontera: list[tuple[float, int, float, str]] = []
    orden = 0
    heapq.heappush(frontera, (heuristica(origen), orden, 0.0, origen))
    mejor = {origen: 0.0}
    padre: dict[str, str | None] = {origen: None}
    cerrados: set[str] = set()
    expandidos = 0

    while frontera:
        _, _, acumulado, actual = heapq.heappop(frontera)
        if actual in cerrados:
            continue
        cerrados.add(actual)
        expandidos += 1
        if actual == destino:
            return _reconstruir(padre, actual), expandidos
        for arista in grafo.vecinos(actual):
            if permitidos is not None and arista.destino not in permitidos:
                continue
            nuevo = acumulado + costo(arista)
            if nuevo + 1e-9 < mejor.get(arista.destino, math.inf):
                mejor[arista.destino] = nuevo
                padre[arista.destino] = actual
                orden += 1
                heapq.heappush(
                    frontera,
                    (nuevo + heuristica(arista.destino), orden, nuevo, arista.destino),
                )
    return None, expandidos


class EstrategiaNavegacion(ABC):
    nombre: str

    @abstractmethod
    def calcular(
        self,
        grafo: GrafoTerminal,
        terminal: ZonaCompuesta,
        origen: str,
        destino: str,
        marea_alta: bool,
    ) -> PlanRuta:
        raise NotImplementedError

    def _plan(
        self,
        grafo: GrafoTerminal,
        origen: str,
        destino: str,
        marea_alta: bool,
        usar_tiempo: bool,
        usar_heuristica: bool,
        permitidos: set[str] | None,
    ) -> PlanRuta:
        inicio = time.perf_counter()
        camino, expandidos = buscar(
            grafo,
            origen,
            destino,
            marea_alta,
            usar_tiempo,
            usar_heuristica,
            permitidos,
        )
        transcurrido = (time.perf_counter() - inicio) * 1000
        if not camino or camino[0] != origen:
            return PlanRuta(self.nombre, [], math.inf, 0.0, expandidos, transcurrido, False)
        tiempo, distancia = _evaluar(grafo, camino, marea_alta)
        return PlanRuta(self.nombre, camino, tiempo, distancia, expandidos, transcurrido, True)


class EstrategiaDistancia(EstrategiaNavegacion):
    """Camino más corto en metros. Ignora congestión y ventana de marea."""

    nombre = "Distancia"

    def calcular(self, grafo, terminal, origen, destino, marea_alta) -> PlanRuta:
        del terminal
        return self._plan(grafo, origen, destino, marea_alta, False, False, None)


class EstrategiaAStar(EstrategiaNavegacion):
    """Costo real (tiempo, congestión y marea) con heurística euclidiana admisible."""

    nombre = "A*"

    def calcular(self, grafo, terminal, origen, destino, marea_alta) -> PlanRuta:
        del terminal
        return self._plan(grafo, origen, destino, marea_alta, True, True, None)


class EstrategiaCostoOptimo(EstrategiaNavegacion):
    """Dijkstra sobre el costo real. Sirve de línea base óptima, sin heurística."""

    nombre = "Dijkstra"

    def calcular(self, grafo, terminal, origen, destino, marea_alta) -> PlanRuta:
        del terminal
        return self._plan(grafo, origen, destino, marea_alta, True, False, None)


class EstrategiaJerarquica(EstrategiaNavegacion):
    """Usa el Composite de zonas: poda áreas no transitables y busca con A*."""

    nombre = "Jerárquica"

    def calcular(self, grafo, terminal, origen, destino, marea_alta) -> PlanRuta:
        excluidos: set[str] = set()
        for hoja in terminal.hojas():
            if hoja.transitable:
                continue
            identificadores = {nodo.id for nodo in hoja.nodos()}
            if origen in identificadores or destino in identificadores:
                continue
            excluidos.update(identificadores)
        permitidos = set(grafo.nodos) - excluidos
        return self._plan(grafo, origen, destino, marea_alta, True, True, permitidos)


def catalogo() -> dict[str, EstrategiaNavegacion]:
    estrategias: list[EstrategiaNavegacion] = [
        EstrategiaDistancia(),
        EstrategiaCostoOptimo(),
        EstrategiaAStar(),
        EstrategiaJerarquica(),
    ]
    return {estrategia.nombre: estrategia for estrategia in estrategias}
