import math
from typing import List, Dict, Tuple

from core.orbit_position import position_in_orbital_plane
from core.coordinate_transforms import orbital_to_inertial
from core.radec import xyz_to_radec
from core.residuals import residuals
from core.time_utils import extract_jd

K = 0.01720209895
MU = K * K


def _clamp_e(e: float) -> float:
    return min(0.9, max(1e-6, e))


def predict_radec_at_time(jd: float, jd0: float, params: Dict) -> Tuple[float, float]:
    a = float(params["a"])
    e = _clamp_e(float(params["e"]))
    Omega = float(params["Omega"])
    inc = float(params["inc"])
    omega = float(params["omega"])
    M0 = float(params["M0"])

    n = math.sqrt(MU / (a ** 3))

    dt_days = jd - jd0
    M = (M0 + n * dt_days) % (2 * math.pi)

    x, y, z, _E = position_in_orbital_plane(a=a, e=e, M=M)

    X, Y, Z = orbital_to_inertial(x, y, z, Omega, inc, omega)

    ra, dec = xyz_to_radec(X, Y, Z)

    ra = ra % (2 * math.pi)

    return ra, dec


def total_cost(observations: List[Dict], params: Dict) -> float:
    if not observations:
        raise ValueError("observations list is empty")

    jd0 = extract_jd(observations[0]["time"])
    S = 0.0

    for obs in observations:
        jd = extract_jd(obs["time"])

        ra_pred, dec_pred = predict_radec_at_time(jd, jd0, params)

        ra_obs = math.radians(float(obs["ra"]))
        dec_obs = math.radians(float(obs["dec"]))

        err_ra, err_dec = residuals(ra_pred, dec_pred, ra_obs, dec_obs)

        err_ra_weighted = err_ra * math.cos(dec_obs)

        S += err_ra_weighted ** 2 + err_dec ** 2

    return S


def rms(observations: List[Dict], params: Dict) -> float:
    S = total_cost(observations, params)
    return math.sqrt(S / len(observations))