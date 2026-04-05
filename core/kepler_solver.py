import math


def wrap_2pi(x: float) -> float:
    return x % (2.0 * math.pi)


def solve_kepler_iterative(M: float, e: float, tol: float = 1e-6, max_iter: int = 100) -> float:
    """
    Solves: M = E - e*sin(E)
    using an iterative correction method (implemented from scratch).

    Inputs/Outputs are radians.
    """
    if not (0.0 <= e < 1.0):
        raise ValueError(f"e must satisfy 0 <= e < 1, got e={e}")

    M = wrap_2pi(M)

    E = M  

    for _ in range(max_iter):
    
        f = E - e * math.sin(E) - M

    
        s = 1.0 - e * math.cos(E)

        if abs(s) < 1e-12:
            s = 1e-12 if s >= 0 else -1e-12

        step = f / s
        E -= step

        if abs(step) < tol:
            return E

    raise RuntimeError("Kepler solver did not converge")
