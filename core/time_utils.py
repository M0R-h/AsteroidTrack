import re

JD_RE = re.compile(r"(\d{7}\.\d+)")  # למשל 2461060.500000000

def extract_jd(t_str: str) -> float:
    """
    Extract Julian Date (JD) float from Horizons time string.
    Works with strings like: '2026-Jan-20 00:00 2461060.500000000'
    """
    m = JD_RE.search(t_str)
    if not m:
        raise ValueError(f"Could not extract JD from t='{t_str}'")
    return float(m.group(1))
