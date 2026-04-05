# core/forward_model.py
import math
from typing import Tuple, Dict, Any

from core.orbit_position import position_in_orbital_plane
from core.coordinate_transforms import orbital_to_inertial
from core.radec import xyz_to_radec
from core.time_utils import extract_jd
from core.observations_loader import load_observations
from core.optimizer_lm import fit_orbit


def wrap_2pi(angle: float) -> float:
    return angle % (2.0 * math.pi)


def clamp_e(e: float) -> float:

    return min(0.9, max(1e-6, e))


def mean_anomaly_at_time(params: Dict[str, float], obs_t_str: str) -> float:
    """
    M(t) = M0 + n*(t - t0)

    params חייב להכיל:
      - M0 (rad)
      - t0_jd (Julian date reference)
    אופציונלי:
      - n (rad/day)  אם אין -> 1.0 כברירת מחדל (דמו/נורמליזציה)
    """
    jd = extract_jd(obs_t_str)
    t0 = params["t0_jd"]
    n = params.get("n", 1.0)  
    M = params["M0"] + n * (jd - t0)
    return wrap_2pi(M)


def forward_model(params: Dict[str, float], obs: Dict[str, Any]) -> Tuple[float, float]:
    """
    קלט:
      params: dict עם
        a, e, Omega, inc, omega, M0 (ברדיאנים),
        t0_jd (JD), ואפשר גם n (rad/day)
      obs: תצפית אחת (dict) שמכילה לפחות:
        obs["t"]  (מחרוזת Horizons עם JD בפנים)

    פלט:
      ra_pred, dec_pred (ברדיאנים)
    """
    a = params["a"]
    e = clamp_e(params["e"])

    Omega = params["Omega"]
    inc = params["inc"]
    omega = params["omega"]

    M = mean_anomaly_at_time(params, obs["t"])

    x_orb, y_orb, z_orb, _E = position_in_orbital_plane(a=a, e=e, M=M)


    X, Y, Z = orbital_to_inertial(x_orb, y_orb, z_orb, Omega=Omega, inc=inc, omega=omega)


    ra, dec = xyz_to_radec(X, Y, Z)

    # RA wrap 
    ra = wrap_2pi(ra)

    return ra, dec

def run_forward_model():
    observations = load_observations("data/observations.json")

    result = fit_orbit(observations)

    return {
        "status": "completed",
        "observations": len(observations),
        "best_rms_deg": result["best_rms_deg"],
        "params": result["best_params"],
    }
