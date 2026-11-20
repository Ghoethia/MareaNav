"""Topología del terminal: nodos, aristas, grafo y zonas compuestas."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


VELOCIDAD_MS = 8.0
ESPERA_MAREA_S = 40 * 60


@dataclass(frozen=True)
class Nodo:
    id: str
    nombre: str
    x: float
    y: float
    zona: str


@dataclass(frozen=True)
class Arista:
    origen: str
    destino: str
    distancia: float
    congestion: float
    requiere_marea_alta: bool = False


class GrafoTerminal:
    """Red navegable del terminal. Las vías se guardan en ambos sentidos."""

    def __init__(self) -> None:
        self.nodos: dict[str, Nodo] = {}
        self.adyacencia: dict[str, list[Arista]] = {}

    def agregar_nodo(self, nodo: Nodo) -> None:
        self.nodos[nodo.id] = nodo
        self.adyacencia.setdefault(nodo.id, [])

    def conectar(
        self,
        origen: str,
        destino: str,
        distancia: float,
        congestion: float,
        requiere_marea_alta: bool = False,
    ) -> None:
        self.adyacencia[origen].append(
            Arista(origen, destino, distancia, congestion, requiere_marea_alta)
        )
        self.adyacencia[destino].append(
            Arista(destino, origen, distancia, congestion, requiere_marea_alta)
        )

    def vecinos(self, nodo_id: str) -> list[Arista]:
        return self.adyacencia.get(nodo_id, [])

    def arista(self, origen: str, destino: str) -> Arista:
        for candidata in self.vecinos(origen):
            if candidata.destino == destino:
                return candidata
        raise KeyError(f"No existe vía {origen} -> {destino}")


def costo_tiempo(arista: Arista, marea_alta: bool) -> float:
    """Segundos reales de cruce. La marea baja suma la espera del canal."""
    factor = 1.0 + (arista.congestion * 3.0)
    tiempo = (arista.distancia / VELOCIDAD_MS) * factor
    if arista.requiere_marea_alta and not marea_alta:
        tiempo += ESPERA_MAREA_S
    return tiempo


def costo_distancia(arista: Arista, marea_alta: bool) -> float:
    """Objetivo de la estrategia corta: metros, sin congestión ni marea."""
    del marea_alta
    return arista.distancia


class Zona(ABC):
    @abstractmethod
    def nombre(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def nodos(self) -> list[Nodo]:
        raise NotImplementedError


class ZonaHoja(Zona):
    def __init__(self, nombre_zona: str, nodos: list[Nodo], transitable: bool = True) -> None:
        self._nombre = nombre_zona
        self._nodos = list(nodos)
        self.transitable = transitable

    def nombre(self) -> str:
        return self._nombre

    def nodos(self) -> list[Nodo]:
        return list(self._nodos)


class ZonaCompuesta(Zona):
    def __init__(self, nombre_zona: str, hijos: list[Zona] | None = None) -> None:
        self._nombre = nombre_zona
        self.hijos: list[Zona] = list(hijos or [])

    def nombre(self) -> str:
        return self._nombre

    def agregar(self, zona: Zona) -> None:
        self.hijos.append(zona)

    def nodos(self) -> list[Nodo]:
        acumulado: list[Nodo] = []
        for hijo in self.hijos:
            acumulado.extend(hijo.nodos())
        return acumulado

    def hojas(self) -> list[ZonaHoja]:
        encontradas: list[ZonaHoja] = []
        for hijo in self.hijos:
            if isinstance(hijo, ZonaHoja):
                encontradas.append(hijo)
            elif isinstance(hijo, ZonaCompuesta):
                encontradas.extend(hijo.hojas())
        return encontradas
