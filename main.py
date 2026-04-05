import json
import math
import random
from pathlib import Path

from core.cost import total_cost, rms
from core.optimizer_lm import levenberg_marquardt_fit
from core.time_utils import extract_jd

DATA_DIR = Path("data")
OBS_PATH = DATA_DIR / "observations.json"
BEST_PATH = DATA_DIR / "best_params.json"


def load_observations_json(path: Path) -> list[dict]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_best_params(params: dict, path: Path):
    out = dict(params)
    # גם רדיאנים וגם מעלות – שיהיה נוח לדוח
    out_deg = {
        "a": params["a"],
        "e": params["e"],
        "Omega_deg": math.degrees(params["Omega"]),
        "inc_deg": math.degrees(params["inc"]),
        "omega_deg": math.degrees(params["omega"]),
        "M0_deg": math.degrees(params["M0"]),
        "t0_jd": params.get("t0_jd"),
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"rad": out, "deg": out_deg}, f, indent=2)


def random_search(observations: list[dict], start_params: dict, trials: int = 1000) -> tuple[dict, float]:
    best = dict(start_params)
    best_S = total_cost(observations, best)
    best_rms = math.sqrt(best_S / len(observations))

    print("\n=== RANDOM SEARCH ===")
    print("Start RMS(deg):", math.degrees(best_rms))
    print("Start S:", best_S)

    for t in range(trials):
        cand = dict(best)

        # קפיצות אקראיות
        cand["a"] = max(0.05, best["a"] * (0.7 + 0.6 * random.random()))  # 0.7a..1.3a
        cand["e"] = min(0.9, max(1e-6, best["e"] + random.uniform(-0.2, 0.2)))  # ✅ לא 0
        cand["Omega"] = (best["Omega"] + random.uniform(-1.0, 1.0)) % (2 * math.pi)
        cand["inc"] = min(math.pi, max(0.0, best["inc"] + random.uniform(-0.5, 0.5)))
        cand["omega"] = (best["omega"] + random.uniform(-1.0, 1.0)) % (2 * math.pi)
        cand["M0"] = (best["M0"] + random.uniform(-1.0, 1.0)) % (2 * math.pi)

        # לשמור גם t0_jd קבוע
        cand["t0_jd"] = best["t0_jd"]

        S = total_cost(observations, cand)
        if S < best_S:
            best_S = S
            best = cand
            best_rms = math.sqrt(best_S / len(observations))
            print(f"[improved @ {t}] S={best_S:.6f} RMS(deg)={math.degrees(best_rms):.6f}")

    print("\n=== RANDOM SEARCH BEST ===")
    print("Best S:", best_S)
    print("Best RMS(deg):", math.degrees(best_rms))
    return best, best_rms
from core.cost import predict_radec_at_time
from core.residuals import residuals
from core.time_utils import extract_jd


def evaluate(params: dict, observations: list[dict], limit: int = 10):
    jd0 = params.get("t0_jd", extract_jd(observations[0]["t"]))
    print("\n=== EVALUATION (final params) ===")

    total = 0.0
    for i, obs in enumerate(observations):
        jd = extract_jd(obs["t"])

        ra_pred, dec_pred = predict_radec_at_time(jd, jd0, params)
        ra_obs = math.radians(obs["ra_deg"])
        dec_obs = math.radians(obs["dec_deg"])

        err_ra, err_dec = residuals(ra_pred, dec_pred, ra_obs, dec_obs)

        err_ra_deg = math.degrees(err_ra)
        err_dec_deg = math.degrees(err_dec)

        total += err_ra**2 + err_dec**2

        if i < limit:
            print(
                f"[{i}] t={obs['t']} | "
                f"RA_obs={obs['ra_deg']:.6f}  DEC_obs={obs['dec_deg']:.6f} | "
                f"RA_err={err_ra_deg:+.6f}  DEC_err={err_dec_deg:+.6f}"
            )

    rms_rad = math.sqrt(total / len(observations))
    print(f"\nFinal RMS(deg): {math.degrees(rms_rad):.6f}")



def main():
    DATA_DIR.mkdir(exist_ok=True)

    observations = load_observations_json(OBS_PATH)
    print("\nLoaded", len(observations), "observations from", OBS_PATH)

    # זמן ייחוס
    t0_jd = extract_jd(observations[0]["t"])

    # ניחוש התחלתי (דמו)
    initial = {
        "a": 1.0,
        "e": 0.1,
        "Omega": math.radians(30),
        "inc": math.radians(20),
        "omega": math.radians(10),
        "M0": 1.0,
        "t0_jd": t0_jd,   # ✅ חובה כדי ש-M(t) יעבוד “לפי הספר”
    }

    print("\n=== INITIAL ===")
    init_rms = rms(observations, initial)
    print("Initial RMS(deg):", math.degrees(init_rms))
    print("Initial S:", total_cost(observations, initial))

    # 1) Random Search – למצוא אזור טוב
    best_rs, best_rs_rms = random_search(observations, initial, trials=1000)

    # 2) LM – שיפור חד ומהיר
    keys = ["a", "e", "Omega", "inc", "omega", "M0"]
    deltas = {
        "a": 1e-3,
        "e": 1e-4,
        "Omega": 1e-4,
        "inc": 1e-4,
        "omega": 1e-4,
        "M0": 1e-4,
    }

    print("\n=== LM (ITERATIVE FIT) ===")
    best_lm, best_lm_rms = levenberg_marquardt_fit(
        observations=observations,
        params=best_rs,
        keys=keys,
        deltas=deltas,
        max_iter=25,
        lam=1e-2,
    )

    print("\n=== SUMMARY ===")
    print("Initial RMS(deg):", math.degrees(init_rms))
    print("After RandomSearch RMS(deg):", math.degrees(best_rs_rms))
    print("After LM RMS(deg):", math.degrees(best_lm_rms))

    print("\n=== FINAL PARAMS ===")
    print("a:", best_lm["a"])
    print("e:", best_lm["e"])
    print("Omega(deg):", math.degrees(best_lm["Omega"]))
    print("inc(deg):", math.degrees(best_lm["inc"]))
    print("omega(deg):", math.degrees(best_lm["omega"]))
    print("M0(deg):", math.degrees(best_lm["M0"]))
    print("t0_jd:", best_lm["t0_jd"])

    save_best_params(best_lm, BEST_PATH)
    print("\nSaved best params to", BEST_PATH)
    evaluate(best_lm, observations, limit=10)


if __name__ == "__main__":
    main()
