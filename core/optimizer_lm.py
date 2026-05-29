import math
import numpy as np

from core.cost import predict_radec_at_time
from core.residuals import residuals
from core.time_utils import extract_jd


def residual_vector(observations: list[dict], params: dict) -> np.ndarray:
    jd0 = extract_jd(observations[0]["time"])
    r = []

    for obs in observations:
        jd = extract_jd(obs["time"])

        ra_pred, dec_pred = predict_radec_at_time(jd, jd0, params)

        # Mongo data מגיע במעלות → ממירים לרדיאנים
        ra_obs = math.radians(obs["ra"])
        dec_obs = math.radians(obs["dec"])

        err_ra, err_dec = residuals(ra_pred, dec_pred, ra_obs, dec_obs)

        # משקל cos(dec)
        err_ra_w = err_ra * math.cos(dec_obs)

        r.append(err_ra_w)
        r.append(err_dec)

    return np.array(r, dtype=float)


def jacobian_fd(observations: list[dict], params: dict, keys: list[str], deltas: dict) -> np.ndarray:
    r0 = residual_vector(observations, params)
    m = r0.size
    n = len(keys)
    J = np.zeros((m, n), dtype=float)

    for k, key in enumerate(keys):
        p2 = dict(params)
        p2[key] = p2[key] + deltas[key]

        r1 = residual_vector(observations, p2)
        J[:, k] = (r1 - r0) / deltas[key]

    return J


def rms_from_residuals(r: np.ndarray, N_obs: int) -> float:
    S = float(r @ r)
    return math.sqrt(S / N_obs)


def levenberg_marquardt_fit(
    observations: list[dict],
    params: dict,
    keys: list[str],
    deltas: dict,
    max_iter: int = 25,
    lam: float = 1e-2
):
    p = dict(params)
    N = len(observations)

    r = residual_vector(observations, p)
    best_rms = rms_from_residuals(r, N)

    print(f"iter=0  RMS(deg)={math.degrees(best_rms):.6f}  lambda={lam}")

    for it in range(1, max_iter + 1):
        J = jacobian_fd(observations, p, keys, deltas)

        A = J.T @ J + lam * np.eye(len(keys))
        g = J.T @ r

        try:
            dp = -np.linalg.solve(A, g)
        except np.linalg.LinAlgError:
            lam *= 10
            print(f"iter={it}  solve failed -> lambda={lam}")
            continue

        p_try = dict(p)

        for i, key in enumerate(keys):
            p_try[key] = p_try[key] + float(dp[i])

            # שמירה על תחומים פיזיקליים
            if key in ("Omega", "omega", "M0"):
                p_try[key] %= (2 * math.pi)

            if key == "inc":
                p_try[key] = min(math.pi, max(0.0, p_try[key]))

            if key == "e":
                p_try[key] = min(0.9, max(1e-6, p_try[key]))

            if key == "a":
                p_try[key] = max(0.05, p_try[key])

        r_try = residual_vector(observations, p_try)
        rms_try = rms_from_residuals(r_try, N)

        if rms_try < best_rms:
            p = p_try
            r = r_try
            best_rms = rms_try
            lam = max(lam / 3, 1e-8)

            print(f"iter={it}  RMS(deg)={math.degrees(best_rms):.6f}  ACCEPT  lambda={lam}")
        else:
            lam *= 5
            print(f"iter={it}  RMS(deg)={math.degrees(rms_try):.6f}  REJECT  lambda={lam}")

    return p, best_rms


def fit_orbit(observations: list[dict]):
    t0_jd = extract_jd(observations[0]["time"])

    initial = {
        "a": 1.0,
        "e": 0.1,
        "Omega": math.radians(30),
        "inc": math.radians(20),
        "omega": math.radians(10),
        "M0": 1.0,
        "t0_jd": t0_jd,
    }

    keys = ["a", "e", "Omega", "inc", "omega", "M0"]

    deltas = {
        "a": 1e-3,
        "e": 1e-4,
        "Omega": 1e-4,
        "inc": 1e-4,
        "omega": 1e-4,
        "M0": 1e-4,
    }

    best_params, best_rms = levenberg_marquardt_fit(
        observations=observations,
        params=initial,
        keys=keys,
        deltas=deltas,
        max_iter=25,
        lam=1e-2,
    )

    return {
        "best_params": best_params,
        "best_rms_deg": math.degrees(best_rms),
    }