import math
from core.kepler_solver import solve_kepler_iterative


def position_in_orbital_plane(a: float, e: float, M: float):
    E = solve_kepler_iterative(M, e)

    x = a * (math.cos(E) - e)
    y = a * math.sqrt(1 - e**2) * math.sin(E)

    return x, y, 0.0, E