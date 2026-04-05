import math

def wrap_pi(x: float) -> float:
    return (x + math.pi) % (2 * math.pi) - math.pi

def angle_diff(a: float, b: float) -> float:
    return wrap_pi(a - b)

def residuals(ra_pred: float, dec_pred: float, ra_obs: float, dec_obs: float):
    # RA wrap + weighting
    err_ra = angle_diff(ra_pred, ra_obs) * math.cos(dec_obs)
    err_dec = dec_pred - dec_obs
    return err_ra, err_dec
