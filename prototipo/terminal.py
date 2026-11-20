"""Construcción del terminal de demostración y de las redes de escala."""

from __future__ import annotations

import math

from prototipo.modelo import GrafoTerminal, Nodo, ZonaCompuesta, ZonaHoja


def _conectar(
    grafo: GrafoTerminal,
    origen: str,
    destino: str,
    congestion: float,
    requiere_marea_alta: bool = False,
) -> None:
    """La longitud de la vía es la distancia euclidiana, para que la heurística sea admisible."""
    a = grafo.nodos[origen]
    b = grafo.nodos[destino]
    distancia = math.hypot(a.x - b.x, a.y - b.y)
    grafo.conectar(origen, destino, distancia, congestion, requiere_marea_alta)


def construir_demostracion(congestion_arteria: float) -> tuple[GrafoTerminal, ZonaCompuesta, str, str]:
    """Red reducida: la arteria y el canal son más cortos; el lateral es más largo.

    El canal depende de la marea. La arteria se congestiona. La bodega no tiene salida al muelle.
    Las coordenadas están en metros y coinciden con la longitud de cada vía.
    """
    especificacion = [
        ("PO", "Acceso de portería", 0, 0, "Acceso"),
        ("CL", "Patio de clasificación", 200, 0, "Clasificación"),
        ("A1", "Tramo arterial 1", 380, 0, "Arteria"),
        ("A2", "Tramo arterial 2", 560, 0, "Arteria"),
        ("CA", "Canal de marea", 650, 30, "Canal"),
        ("MU", "Muelle de despacho", 760, 0, "Muelle"),
        ("L1", "Calle lateral 1", 280, 220, "Lateral"),
        ("L2", "Calle lateral 2", 480, 260, "Lateral"),
        ("L3", "Calle lateral 3", 680, 200, "Lateral"),
        ("B1", "Bodega módulo 1", 200, 50, "Bodega"),
        ("B2", "Bodega módulo 2", 200, 100, "Bodega"),
        ("B3", "Bodega módulo 3", 150, 100, "Bodega"),
        ("B4", "Bodega módulo 4", 150, 150, "Bodega"),
        ("B5", "Bodega módulo 5", 200, 150, "Bodega"),
        ("B6", "Bodega módulo 6", 250, 150, "Bodega"),
        ("B7", "Bodega módulo 7", 250, 100, "Bodega"),
        ("B8", "Bodega módulo 8", 300, 100, "Bodega"),
    ]
    grafo = GrafoTerminal()
    for identificador, nombre, x, y, zona in especificacion:
        grafo.agregar_nodo(Nodo(identificador, nombre, float(x), float(y), zona))

    arteria = congestion_arteria
    _conectar(grafo, "PO", "CL", 0.08)
    _conectar(grafo, "CL", "A1", arteria)
    _conectar(grafo, "A1", "A2", arteria)
    _conectar(grafo, "A2", "CA", 0.04, True)
    _conectar(grafo, "CA", "MU", 0.04, True)
    _conectar(grafo, "A2", "L3", 0.05)
    _conectar(grafo, "CL", "L1", 0.05)
    _conectar(grafo, "L1", "L2", 0.05)
    _conectar(grafo, "L2", "L3", 0.05)
    _conectar(grafo, "L3", "MU", 0.05)
    for origen, destino in (
        ("CL", "B1"),
        ("B1", "B2"),
        ("B2", "B3"),
        ("B3", "B4"),
        ("B4", "B5"),
        ("B5", "B6"),
        ("B6", "B7"),
        ("B7", "B8"),
    ):
        _conectar(grafo, origen, destino, 0.0)

    por_zona: dict[str, list[Nodo]] = {}
    for nodo in grafo.nodos.values():
        por_zona.setdefault(nodo.zona, []).append(nodo)

    terminal = ZonaCompuesta("Terminal MareaNav")
    operacion = ZonaCompuesta("Zona operativa")
    for nombre in ("Acceso", "Clasificación", "Arteria", "Lateral", "Canal", "Muelle"):
        operacion.agregar(ZonaHoja(nombre, por_zona[nombre], transitable=True))
    terminal.agregar(operacion)
    terminal.agregar(ZonaHoja("Bodega", por_zona["Bodega"], transitable=False))
    return grafo, terminal, "PO", "MU"


def construir_escala(lado: int, congestion_arteria: float = 0.55) -> tuple[GrafoTerminal, ZonaCompuesta, str, str]:
    """Dos mallas: corredor hacia el muelle y bodega en sentido contrario, sin salida."""
    grafo = GrafoTerminal()
    paso_corredor = 100.0
    paso_bodega = 25.0

    def identificador(prefijo: str, fila: int, columna: int) -> str:
        return f"{prefijo}-{fila}-{columna}"

    corredor: list[Nodo] = []
    bodega: list[Nodo] = []
    for fila in range(lado):
        for columna in range(lado):
            nodo_corredor = Nodo(
                identificador("C", fila, columna),
                f"Corredor {fila}-{columna}",
                120 + columna * paso_corredor,
                (fila - (lado // 2)) * paso_corredor,
                "Corredor",
            )
            nodo_bodega = Nodo(
                identificador("B", fila, columna),
                f"Bodega {fila}-{columna}",
                -40 - columna * paso_bodega,
                (fila - (lado // 2)) * paso_bodega,
                "Bodega",
            )
            grafo.agregar_nodo(nodo_corredor)
            grafo.agregar_nodo(nodo_bodega)
            corredor.append(nodo_corredor)
            bodega.append(nodo_bodega)

    fila_media = lado // 2
    acceso = Nodo("S", "Acceso", 0.0, 0.0, "Acceso")
    muelle = Nodo("T", "Muelle", 120 + lado * paso_corredor + 80, 0.0, "Muelle")
    grafo.agregar_nodo(acceso)
    grafo.agregar_nodo(muelle)

    for fila in range(lado):
        for columna in range(lado):
            actual = identificador("C", fila, columna)
            congestion = congestion_arteria if fila == fila_media else 0.05
            if columna + 1 < lado:
                _conectar(grafo, actual, identificador("C", fila, columna + 1), congestion)
            if fila + 1 < lado:
                _conectar(grafo, actual, identificador("C", fila + 1, columna), 0.05)
            bodega_actual = identificador("B", fila, columna)
            if columna + 1 < lado:
                _conectar(grafo, bodega_actual, identificador("B", fila, columna + 1), 0.0)
            if fila + 1 < lado:
                _conectar(grafo, bodega_actual, identificador("B", fila + 1, columna), 0.0)

    _conectar(grafo, "S", identificador("C", fila_media, 0), 0.08)
    _conectar(grafo, identificador("C", fila_media, lado - 1), "T", 0.08)
    _conectar(grafo, "S", identificador("B", fila_media, 0), 0.0)

    terminal = ZonaCompuesta("Terminal a escala")
    terminal.agregar(ZonaHoja("Acceso", [acceso], transitable=True))
    terminal.agregar(ZonaHoja("Corredor", corredor, transitable=True))
    terminal.agregar(ZonaHoja("Muelle", [muelle], transitable=True))
    terminal.agregar(ZonaHoja("Bodega", bodega, transitable=False))
    return grafo, terminal, "S", "T"
