"""Command, Observer, Iterator y el contexto que intercambia estrategias."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from prototipo.estrategias import (
    EstrategiaAStar,
    EstrategiaDistancia,
    EstrategiaNavegacion,
    PlanRuta,
)
from prototipo.modelo import GrafoTerminal, Nodo, ZonaCompuesta


class ContextoNavegacion:
    """Mantiene la estrategia vigente y delega el cálculo."""

    def __init__(self, estrategia: EstrategiaNavegacion) -> None:
        self.estrategia = estrategia

    def fijar(self, estrategia: EstrategiaNavegacion) -> None:
        self.estrategia = estrategia

    def calcular(
        self,
        grafo: GrafoTerminal,
        terminal: ZonaCompuesta,
        origen: str,
        destino: str,
        marea_alta: bool,
    ) -> PlanRuta:
        return self.estrategia.calcular(grafo, terminal, origen, destino, marea_alta)


@dataclass
class EstadoTerminal:
    congestion_arteria: float
    marea_alta: bool


class Observador(ABC):
    @abstractmethod
    def actualizar(self, estado: EstadoTerminal) -> None:
        raise NotImplementedError


class MonitorTerminal:
    """Sujeto observable: publica congestión de la arteria y estado de la marea."""

    def __init__(self, estado: EstadoTerminal) -> None:
        self.estado = estado
        self._observadores: list[Observador] = []

    def suscribir(self, observador: Observador) -> None:
        self._observadores.append(observador)

    def fijar(self, congestion_arteria: float, marea_alta: bool) -> None:
        self.estado = EstadoTerminal(congestion_arteria, marea_alta)
        for observador in self._observadores:
            observador.actualizar(self.estado)


class PlanificadorReactivo(Observador):
    """Elige estrategia según el estado publicado por el monitor.

    Condición estable (marea alta y congestión menor a 0,45): distancia.
    Condición adversa (marea baja o arteria congestionada): A*.
    """

    UMBRAL_CONGESTION = 0.45

    def __init__(self, contexto: ContextoNavegacion) -> None:
        self.contexto = contexto
        self.motivo = "inicial"

    def actualizar(self, estado: EstadoTerminal) -> None:
        if not estado.marea_alta:
            self.contexto.fijar(EstrategiaAStar())
            self.motivo = "marea baja: se prioriza el costo real para evitar la espera del canal"
        elif estado.congestion_arteria >= self.UMBRAL_CONGESTION:
            self.contexto.fijar(EstrategiaAStar())
            self.motivo = "congestión alta: se prioriza el tiempo real de recorrido"
        else:
            self.contexto.fijar(EstrategiaDistancia())
            self.motivo = "condición estable: la distancia corta es suficiente"


class Comando(ABC):
    @abstractmethod
    def ejecutar(self) -> PlanRuta:
        raise NotImplementedError

    @abstractmethod
    def deshacer(self) -> None:
        raise NotImplementedError


@dataclass
class RegistroComando:
    origen: str
    destino: str
    estrategia: str
    exito: bool


class ComandoCalcularRuta(Comando):
    def __init__(self, navegador: "NavegadorMareas", origen: str, destino: str) -> None:
        self.navegador = navegador
        self.origen = origen
        self.destino = destino
        self.plan: PlanRuta | None = None
        self._anterior: PlanRuta | None = None

    def ejecutar(self) -> PlanRuta:
        self._anterior = self.navegador.plan_vigente
        self.plan = self.navegador.contexto.calcular(
            self.navegador.grafo,
            self.navegador.terminal,
            self.origen,
            self.destino,
            self.navegador.monitor.estado.marea_alta,
        )
        self.navegador.plan_vigente = self.plan
        return self.plan

    def deshacer(self) -> None:
        self.navegador.plan_vigente = self._anterior


class InvocadorDespacho:
    def __init__(self) -> None:
        self._pila: list[ComandoCalcularRuta] = []
        self._bitacora: list[ComandoCalcularRuta] = []

    def ejecutar(self, comando: ComandoCalcularRuta) -> PlanRuta:
        plan = comando.ejecutar()
        self._pila.append(comando)
        self._bitacora.append(comando)
        return plan

    def deshacer(self) -> bool:
        if not self._pila:
            return False
        self._pila.pop().deshacer()
        return True

    def bitacora(self) -> list[RegistroComando]:
        registros = []
        for comando in self._bitacora:
            plan = comando.plan
            registros.append(
                RegistroComando(
                    comando.origen,
                    comando.destino,
                    plan.estrategia if plan else "",
                    bool(plan and plan.exito),
                )
            )
        return registros


class IteradorRuta:
    """Recorre el itinerario sin exponer la lista interna del plan."""

    def __init__(self, camino: list[str], grafo: GrafoTerminal) -> None:
        self._camino = camino
        self._grafo = grafo
        self._indice = 0

    def __iter__(self) -> "IteradorRuta":
        return self

    def __next__(self) -> Nodo:
        if self._indice >= len(self._camino):
            raise StopIteration
        nodo = self._grafo.nodos[self._camino[self._indice]]
        self._indice += 1
        return nodo


@dataclass
class NavegadorMareas:
    """Fachada que integra estrategia, observador, comando e iterador."""

    grafo: GrafoTerminal
    terminal: ZonaCompuesta
    contexto: ContextoNavegacion
    monitor: MonitorTerminal
    planificador: PlanificadorReactivo
    invocador: InvocadorDespacho = field(default_factory=InvocadorDespacho)
    plan_vigente: PlanRuta | None = None

    @classmethod
    def crear(
        cls,
        grafo: GrafoTerminal,
        terminal: ZonaCompuesta,
        congestion: float,
        marea_alta: bool,
    ) -> "NavegadorMareas":
        contexto = ContextoNavegacion(EstrategiaDistancia())
        planificador = PlanificadorReactivo(contexto)
        monitor = MonitorTerminal(EstadoTerminal(congestion, marea_alta))
        monitor.suscribir(planificador)
        planificador.actualizar(monitor.estado)
        return cls(grafo, terminal, contexto, monitor, planificador)

    def calcular(self, origen: str, destino: str) -> PlanRuta:
        comando = ComandoCalcularRuta(self, origen, destino)
        return self.invocador.ejecutar(comando)

    def deshacer(self) -> bool:
        return self.invocador.deshacer()

    def itinerario(self, plan: PlanRuta | None = None) -> list[str]:
        vigente = plan or self.plan_vigente
        if not vigente or not vigente.camino:
            return []
        return [nodo.nombre for nodo in IteradorRuta(vigente.camino, self.grafo)]
