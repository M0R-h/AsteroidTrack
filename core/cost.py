import math
from typing import List, Dict, Tuple

from core.orbit_position import position_in_orbital_plane
from core.coordinate_transforms import orbital_to_inertial
from core.radec import xyz_to_radec
from core.residuals import residuals
from core.time_utils import extract_jd

# Gaussian gravitational constant (AU^(3/2)/day)
K = 0.01720209895
MU = K * K  # AU^3 / day^2


def _clamp_e(e: float) -> float:
    # prevent e from collapsing to 0 or exploding to 1
    return min(0.9, max(1e-6, e))


def predict_radec_at_time(jd: float, jd0: float, params: Dict) -> Tuple[float, float]:
    """
    Predict (RA, DEC) in radians at Julian Date 'jd' given orbital elements in 'params'.
    params expects:
      a (AU), e, Omega (rad), inc (rad), omega (rad), M0 (rad)
    """
    a = float(params["a"])
    e = _clamp_e(float(params["e"]))
    Omega = float(params["Omega"])
    inc = float(params["inc"])
    omega = float(params["omega"])
    M0 = float(params["M0"])

    # mean motion (rad/day)
    n = math.sqrt(MU / (a ** 3))

    dt_days = jd - jd0
    M = (M0 + n * dt_days) % (2 * math.pi)  # keep M in [0, 2π)

    # position in orbital plane
    x, y, z, _E = position_in_orbital_plane(a=a, e=e, M=M)

    # rotate to inertial coordinates
    X, Y, Z = orbital_to_inertial(x, y, z, Omega, inc, omega)

    # convert to RA/DEC
    ra, dec = xyz_to_radec(X, Y, Z)

    # wrap RA to [0, 2π)
    ra = ra % (2 * math.pi)

    return ra, dec


def total_cost(observations: List[Dict], params: Dict) -> float:
    """
    S = sum_i [ (ΔRA*cos(DEC_obs))^2 + (ΔDEC)^2 ]
    All angles in radians.
    """
    if not observations:
        raise ValueError("observations list is empty")

    jd0 = extract_jd(observations[0]["t"])
    S = 0.0

    for obs in observations:
        jd = extract_jd(obs["t"])
        ra_pred, dec_pred = predict_radec_at_time(jd, jd0, params)

        ra_obs = math.radians(float(obs["ra_deg"]))
        dec_obs = math.radians(float(obs["dec_deg"]))

        # residuals: ΔRA already wrapped inside angle_diff; ΔDEC direct
        err_ra, err_dec = residuals(ra_pred, dec_pred, ra_obs, dec_obs)

        # spherical weighting for RA component
        err_ra_weighted = err_ra * math.cos(dec_obs)

        S += err_ra_weighted**2 + err_dec**2

    return S


def rms(observations: List[Dict], params: Dict) -> float:
    """
    RMS = sqrt(S / N)
    """
    S = total_cost(observations, params)
    return math.sqrt(S / len(observations))
