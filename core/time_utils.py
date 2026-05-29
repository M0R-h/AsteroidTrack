import re
from datetime import datetime, timezone

JD_RE = re.compile(r"(\d{7}\.\d+)")


def datetime_to_julian_date(dt: datetime) -> float:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    year = dt.year
    month = dt.month

    day = (
        dt.day
        + dt.hour / 24
        + dt.minute / 1440
        + dt.second / 86400
        + dt.microsecond / 86400000000
    )

    if month <= 2:
        year -= 1
        month += 12

    a = year // 100
    b = 2 - a + (a // 4)

    jd = int(365.25 * (year + 4716)) + int(30.6001 * (month + 1)) + day + b - 1524.5

    return jd


def extract_jd(t_str: str) -> float:
    """
    Supports:
    1. Horizons strings with JD inside.
    2. ISO strings like 2026-03-10T00:00:00.
    """
    m = JD_RE.search(t_str)

    if m:
        return float(m.group(1))

    try:
        dt = datetime.fromisoformat(t_str.replace("Z", "+00:00"))
        return datetime_to_julian_date(dt)
    except Exception:
        raise ValueError(f"Could not extract JD from t='{t_str}'")