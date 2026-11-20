"""Punto de entrada: python -m prototipo"""

from prototipo.benchmark import ejecutar, guardar


def main() -> None:
    metricas = ejecutar()
    destino = guardar(metricas)
    print(f"Métricas guardadas en {destino}")
    for escenario in metricas["escenarios"]:
        print(f"\n{escenario['titulo']} | política: {escenario['politica']['estrategia']}")
        print(f"{'Estrategia':<14}{'Tiempo real (s)':>16}{'Metros':>10}{'Expandidos':>12}{'Cálculo (ms)':>14}")
        for fila in escenario["resultados"]:
            print(
                f"{fila['estrategia']:<14}{fila['costo_real_s']:>16.1f}"
                f"{fila['distancia_m']:>10.0f}{fila['nodos_expandidos']:>12}"
                f"{fila['tiempo_calculo_ms']:>14.3f}"
            )
            print("   ruta:", " -> ".join(fila["camino"]))
    print("\nEscalabilidad (nodos expandidos)")
    for fila in metricas["escalabilidad"]:
        resumen = ", ".join(
            f"{item['estrategia']}={item['nodos_expandidos']}" for item in fila["estrategias"]
        )
        print(f"  {fila['nodos']} nodos: {resumen}")


if __name__ == "__main__":
    main()
