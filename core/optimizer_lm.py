import math
import numpy as np

from core.cost import predict_radec_at_time, rms
from core.residuals import residuals
from core.time_utils import extract_jd


def residual_components_for_observation(obs: dict, params: dict, jd0: float):
    jd = extract_jd(obs["time"])

    ra_pred, dec_pred = predict_radec_at_time(jd, jd0, params)

    ra_obs = math.radians(obs["ra"])
    dec_obs = math.radians(obs["dec"])

    err_ra, err_dec = residuals(ra_pred, dec_pred, ra_obs, dec_obs)

    # תיקון RA לפי cos(DEC)
    err_ra_w = err_ra * math.cos(dec_obs)

    # גודל שארית כולל לתצפית
    ri = math.sqrt(err_ra_w ** 2 + err_dec ** 2)

    return err_ra_w, err_dec, ri


def observation_residual_norms(observations: list[dict], params: dict) -> np.ndarray:
    jd0 = extract_jd(observations[0]["time"])
    norms = []

    for obs in observations:
        _, _, ri = residual_components_for_observation(obs, params, jd0)
        norms.append(ri)

    return np.array(norms, dtype=float)


def robust_weights_from_residuals(
    residual_norms: np.ndarray,
    c: float = 2.5,
    min_weight: float = 0.15
) -> np.ndarray:
    """
    בונה משקלים רובוסטיים לפי סף המבוסס על MAD.
    תצפיות רגילות מקבלות משקל 1.
    תצפיות חריגות מקבלות משקל קטן יותר.
    """
    if residual_norms.size == 0:
        return np.array([], dtype=float)

    median = float(np.median(residual_norms))
    mad = float(np.median(np.abs(residual_norms - median)))

    # אם אין פיזור כמעט בכלל
    if mad < 1e-12:
        return np.ones_like(residual_norms, dtype=float)

    robust_sigma = 1.4826 * mad
    threshold = c * robust_sigma

    weights = np.ones_like(residual_norms, dtype=float)

    for i, ri in enumerate(residual_norms):
        if ri > threshold:
            # down-weighting רך ולא מחיקה
            wi = threshold / ri
            weights[i] = max(min_weight, wi)

    return weights


def residual_vector(
    observations: list[dict],
    params: dict,
    weights: np.ndarray | None = None
) -> np.ndarray:
    jd0 = extract_jd(observations[0]["time"])
    r = []

    if weights is None:
        weights = np.ones(len(observations), dtype=float)

    for i, obs in enumerate(observations):
        err_ra_w, err_dec, _ = residual_components_for_observation(obs, params, jd0)

        # weighted least squares -> מכפילים ב-sqrt(w)
        sw = math.sqrt(float(weights[i]))

        r.append(sw * err_ra_w)
        r.append(sw * err_dec)

    return np.array(r, dtype=float)


def jacobian_fd(
    observations: list[dict],
    params: dict,
    keys: list[str],
    deltas: dict,
    weights: np.ndarray | None = None
) -> np.ndarray:
    r0 = residual_vector(observations, params, weights=weights)
    m = r0.size
    n = len(keys)
    J = np.zeros((m, n), dtype=float)

    for k, key in enumerate(keys):
        p2 = dict(params)
        p2[key] = p2[key] + deltas[key]

        r1 = residual_vector(observations, p2, weights=weights)
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
    weights: np.ndarray | None = None,
    max_iter: int = 25,
    lam: float = 1e-2
):
    p = dict(params)
    N = len(observations)

    r = residual_vector(observations, p, weights=weights)
    best_rms = rms_from_residuals(r, N)

    print(f"iter=0  weighted RMS(deg)={math.degrees(best_rms):.6f}  lambda={lam}")

    for it in range(1, max_iter + 1):
        J = jacobian_fd(observations, p, keys, deltas, weights=weights)

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

            # תחומים פיזיקליים
            if key in ("Omega", "omega", "M0"):
                p_try[key] %= (2 * math.pi)

            if key == "inc":
                p_try[key] = min(math.pi, max(0.0, p_try[key]))

            if key == "e":
                p_try[key] = min(0.9, max(1e-6, p_try[key]))

            if key == "a":
                p_try[key] = max(0.05, p_try[key])

        r_try = residual_vector(observations, p_try, weights=weights)
        rms_try = rms_from_residuals(r_try, N)

        if rms_try < best_rms:
            p = p_try
            r = r_try
            best_rms = rms_try
            lam = max(lam / 3, 1e-8)
            print(f"iter={it}  weighted RMS(deg)={math.degrees(best_rms):.6f}  ACCEPT  lambda={lam}")
        else:
            lam *= 5
            print(f"iter={it}  weighted RMS(deg)={math.degrees(rms_try):.6f}  REJECT  lambda={lam}")

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

    # שלב 1: התאמה ראשונית ללא משקלים
    first_params, first_weighted_rms = levenberg_marquardt_fit(
        observations=observations,
        params=initial,
        keys=keys,
        deltas=deltas,
        weights=None,
        max_iter=20,
        lam=1e-2,
    )

    # שלב 2: חישוב שאריות לכל תצפית
    residual_norms = observation_residual_norms(observations, first_params)

    # שלב 3: בניית משקלים רובוסטיים
    weights = robust_weights_from_residuals(
        residual_norms=residual_norms,
        c=2.5,
        min_weight=0.15,
    )

    # שלב 4: התאמה מחדש עם משקלים
    best_params, best_weighted_rms = levenberg_marquardt_fit(
        observations=observations,
        params=first_params,
        keys=keys,
        deltas=deltas,
        weights=weights,
        max_iter=20,
        lam=1e-2,
    )

    best_rms_unweighted_deg = math.degrees(rms(observations, best_params))

    outlier_count = int(np.sum(weights < 0.999))
    
    print("best_rms_deg =", best_rms_unweighted_deg)
    print("weighted_rms_deg =", math.degrees(best_weighted_rms))
    print("outlier_count =", outlier_count)

    return {
        "best_params": best_params,
        "best_rms_deg": best_rms_unweighted_deg,
        "weighted_rms_deg": math.degrees(best_weighted_rms),
        "weights": weights.tolist(),
        "residual_norms": residual_norms.tolist(),
        "outlier_count": outlier_count,
    }