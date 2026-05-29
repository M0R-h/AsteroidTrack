from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import math

from core.kepler_solver import solve_kepler_iterative
from core.orbit_position import position_in_orbital_plane
from core.coordinate_transforms import orbital_to_inertial
from core.cost import predict_radec_at_time


def asteroid_xyz_at_time(orbital_elements: Dict, jd: float, jd0: float) -> Tuple[float, float, float]:
    a = float(orbital_elements["a"])
    e = min(0.9, max(1e-6, float(orbital_elements["e"])))
    m0 = float(orbital_elements["M0"])
    omega = float(orbital_elements["omega"])
    inc = float(orbital_elements["inc"])
    Omega = float(orbital_elements["Omega"])

    k = 0.01720209895
    mu = k * k

    n = math.sqrt(mu / (a ** 3))
    mean_anomaly = (m0 + n * (jd - jd0)) % (2 * math.pi)

    x_orb, y_orb, z_orb, _ = position_in_orbital_plane(a=a, e=e, M=mean_anomaly)
    X, Y, Z = orbital_to_inertial(
        x_orb, y_orb, z_orb,
        Omega=Omega,
        inc=inc,
        omega=omega
    )

    return X, Y, Z


def earth_xyz_approx(jd: float, jd_ref: float) -> Tuple[float, float, float]:
    a = 1.0
    e = 0.0167
    m0 = 0.0

    k = 0.01720209895
    mu = k * k

    n = math.sqrt(mu / (a ** 3))
    mean_anomaly = (m0 + n * (jd - jd_ref)) % (2 * math.pi)
    eccentric_anomaly = solve_kepler_iterative(mean_anomaly, e)

    x_orb = a * (math.cos(eccentric_anomaly) - e)
    y_orb = a * math.sqrt(1 - e ** 2) * math.sin(eccentric_anomaly)
    z_orb = 0.0

    return x_orb, y_orb, z_orb


def calculate_distance_from_sun_au(orbital_elements: Dict, jd: float, jd0: float) -> float:
    a = float(orbital_elements["a"])
    e = min(0.9, max(1e-6, float(orbital_elements["e"])))
    m0 = float(orbital_elements["M0"])

    k = 0.01720209895
    mu = k * k

    n = math.sqrt(mu / (a ** 3))
    mean_anomaly = (m0 + n * (jd - jd0)) % (2 * math.pi)
    eccentric_anomaly = solve_kepler_iterative(mean_anomaly, e)

    return a * (1 - e * math.cos(eccentric_anomaly))


def calculate_distance_from_earth_au(orbital_elements: Dict, jd: float, jd0: float) -> float:
    asteroid_x, asteroid_y, asteroid_z = asteroid_xyz_at_time(orbital_elements, jd, jd0)
    earth_x, earth_y, earth_z = earth_xyz_approx(jd, jd0)

    return math.sqrt(
        (asteroid_x - earth_x) ** 2 +
        (asteroid_y - earth_y) ** 2 +
        (asteroid_z - earth_z) ** 2
    )


def generate_predictions(orbital_elements, start_time, start_jd, days_ahead=365) -> List[Dict]:
    predictions = []

    jd0 = orbital_elements["t0_jd"]

    for i in range(days_ahead):
        future_time = start_time + timedelta(days=i)
        jd = start_jd + i

        ra, dec = predict_radec_at_time(jd, jd0, orbital_elements)
        distance_from_sun_au = calculate_distance_from_sun_au(orbital_elements, jd, jd0)
        distance_from_earth_au = calculate_distance_from_earth_au(orbital_elements, jd, jd0)

        predictions.append({
            "time": future_time.isoformat(),
            "ra": ra,
            "dec": dec,
            "distanceFromSunAU": distance_from_sun_au,
            "distanceFromEarthAU": distance_from_earth_au,
        })

    return predictions