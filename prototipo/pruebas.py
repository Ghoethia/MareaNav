"""Pruebas del prototipo MareaNav."""

from __future__ import annotations

import unittest

from prototipo.estrategias import catalogo
from prototipo.patrones import NavegadorMareas
from prototipo.terminal import construir_demostracion, construir_escala


def _plan(nombre: str, congestion: float, marea_alta: bool):
    grafo, terminal, origen, destino = construir_demostracion(congestion)
    plan = catalogo()[nombre].calcular(grafo, terminal, origen, destino, marea_alta)
    return plan


class PruebasNavegacion(unittest.TestCase):
    def test_astar_conserva_el_optimo_de_dijkstra(self) -> None:
        for congestion, marea in ((0.10, True), (0.85, True), (0.20, False)):
            astar = _plan("A*", congestion, marea)
            dijkstra = _plan("Dijkstra", congestion, marea)
            self.assertTrue(astar.exito and dijkstra.exito)
            self.assertAlmostEqual(astar.costo_real_s, dijkstra.costo_real_s, places=6)

    def test_congestion_alta_penaliza_la_distancia_corta(self) -> None:
        distancia = _plan("Distancia", 0.85, True)
        optimo = _plan("A*", 0.85, True)
        self.assertGreater(distancia.costo_real_s, optimo.costo_real_s * 1.15)
        self.assertLess(distancia.distancia_m, optimo.distancia_m)

    def test_marea_baja_hace_inaceptable_el_canal(self) -> None:
        distancia = _plan("Distancia", 0.20, False)
        optimo = _plan("A*", 0.20, False)
        self.assertIn("CA", distancia.camino)
        self.assertNotIn("CA", optimo.camino)
        self.assertGreater(distancia.costo_real_s, optimo.costo_real_s + 1800)

    def test_condicion_estable_no_degrada_el_tiempo(self) -> None:
        distancia = _plan("Distancia", 0.10, True)
        optimo = _plan("A*", 0.10, True)
        self.assertLessEqual(distancia.costo_real_s, optimo.costo_real_s * 1.05)

    def test_jerarquica_iguala_el_optimo_y_expande_menos_en_la_malla(self) -> None:
        grafo, terminal, origen, destino = construir_escala(10)
        dijkstra = catalogo()["Dijkstra"].calcular(grafo, terminal, origen, destino, True)
        jerarquica = catalogo()["Jerárquica"].calcular(grafo, terminal, origen, destino, True)
        astar = catalogo()["A*"].calcular(grafo, terminal, origen, destino, True)
        self.assertTrue(jerarquica.exito)
        self.assertAlmostEqual(jerarquica.costo_real_s, dijkstra.costo_real_s, places=5)
        self.assertLess(jerarquica.nodos_expandidos, dijkstra.nodos_expandidos)
        self.assertLessEqual(astar.nodos_expandidos, dijkstra.nodos_expandidos)

    def test_observador_cambia_la_estrategia(self) -> None:
        grafo, terminal, origen, destino = construir_demostracion(0.10)
        navegador = NavegadorMareas.crear(grafo, terminal, 0.10, True)
        self.assertEqual(navegador.contexto.estrategia.nombre, "Distancia")
        navegador.monitor.fijar(0.85, True)
        self.assertEqual(navegador.contexto.estrategia.nombre, "A*")
        navegador.monitor.fijar(0.10, False)
        self.assertEqual(navegador.contexto.estrategia.nombre, "A*")
        del origen, destino

    def test_comando_deshace_el_plan_vigente(self) -> None:
        grafo, terminal, origen, destino = construir_demostracion(0.85)
        navegador = NavegadorMareas.crear(grafo, terminal, 0.85, True)
        primero = navegador.calcular(origen, destino)
        navegador.monitor.fijar(0.10, True)
        navegador.calcular(origen, destino)
        self.assertTrue(navegador.deshacer())
        self.assertEqual(navegador.plan_vigente.camino, primero.camino)
        self.assertEqual(len(navegador.invocador.bitacora()), 2)

    def test_iterador_recorre_el_itinerario_completo(self) -> None:
        grafo, terminal, origen, destino = construir_demostracion(0.20)
        navegador = NavegadorMareas.crear(grafo, terminal, 0.20, False)
        plan = navegador.calcular(origen, destino)
        nombres = navegador.itinerario(plan)
        self.assertEqual(len(nombres), len(plan.camino))
        self.assertEqual(nombres[0], "Acceso de portería")
        self.assertEqual(nombres[-1], "Muelle de despacho")

    def test_composite_reune_todos_los_nodos_y_marca_la_bodega(self) -> None:
        grafo, terminal, _, _ = construir_demostracion(0.2)
        self.assertEqual(len(terminal.nodos()), len(grafo.nodos))
        bodega = next(hoja for hoja in terminal.hojas() if hoja.nombre() == "Bodega")
        self.assertFalse(bodega.transitable)
        self.assertGreaterEqual(len(bodega.nodos()), 8)


if __name__ == "__main__":
    unittest.main()
