import json
import re
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional
from urllib.parse import urlencode

import requests


HORIZONS_ENDPOINT = "https://ssd.jpl.nasa.gov/api/horizons.api"


@dataclass
class Observation:
    t: str         # ISO string (UTC-ish)
    ra_deg: float
    dec_deg: float
    source: str = "JPL Horizons"


def _extract_soe_block(text: str) -> str:
    """
    Extract the ephemeris body between $$SOE and $$EOE.
    """
    m = re.search(r"\$\$SOE(.*?)\$\$EOE", text, flags=re.DOTALL)
    if not m:
        raise ValueError("Could not find $$SOE/$$EOE block in Horizons response.")
    return m.group(1).strip()


def _parse_csv_lines(block: str) -> List[List[str]]:
    """
    Split block into CSV-like rows (already comma separated).
    """
    lines = [ln.strip() for ln in block.splitlines() if ln.strip()]
    rows = [ln.split(",") for ln in lines]
    return rows


def fetch_observations(
    command: str,
    start_time: str,
    stop_time: str,
    step_size: str,
    center: str = "500@399",
    quantities: str = "1,9,20,23,24",
    extra_prec: bool = True,
) -> List[Observation]:
    """
    Fetch observer ephemeris from JPL Horizons API and return list of observations.

    command: target, e.g. "433" or "DES=433" or "DES=99942"
    start_time/stop_time: e.g. "2026-01-20 00:00:00"
    step_size: e.g. "1 h" or "10 min" or "1 d"
    center: observer location/center, default geocentric Earth "500@399"
    quantities: Horizons quantities list (includes RA/DEC in observer tables)
    """
    params = {
        "format": "text",
        "COMMAND": f"'{command}'",
        "OBJ_DATA": "'NO'",
        "MAKE_EPHEM": "'YES'",
        "EPHEM_TYPE": "'OBSERVER'",
        "CENTER": f"'{center}'",
        "START_TIME": f"'{start_time}'",
        "STOP_TIME": f"'{stop_time}'",
        "STEP_SIZE": f"'{step_size}'",
        "QUANTITIES": f"'{quantities}'",
        "CSV_FORMAT": "'YES'",
        "EXTRA_PREC": "'YES'" if extra_prec else "'NO'",
        "ANG_FORMAT": "'DEG'",
        "CAL_FORMAT": "'BOTH'",
    }

    url = f"{HORIZONS_ENDPOINT}?{urlencode(params)}"
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    text = resp.text

    block = _extract_soe_block(text)
    rows = _parse_csv_lines(block)

    observations: List[Observation] = []

    # Horizons CSV rows typically begin with date/time fields; exact column names can vary.
    # We'll assume:
    #   col0 = calendar date
    #   col1 = time (or combined)
    # and RA/DEC appear in later columns.
    #
    # Because formats vary, we’ll use a simple robust heuristic:
    # - find columns that look like RA/DEC in degrees: both are floats, DEC can be negative.
    # We'll take the last 2 float-like columns as (RA, DEC) if possible.
    for row in rows:
        # merge date+time if both exist
        t_str = None
        if len(row) >= 2 and re.search(r"\d", row[0]) and re.search(r"\d", row[1]):
            # e.g. "2026-Jan-20", "00:00"
            t_str = f"{row[0].strip()} {row[1].strip()}"
        else:
            t_str = row[0].strip()

        # collect float-like cells
        float_cells = []
        for cell in row:
            cell2 = cell.strip()
            if re.fullmatch(r"[-+]?\d+(\.\d+)?", cell2):
                float_cells.append(float(cell2))

        if len(float_cells) < 2:
            continue

        ra_deg = float_cells[-2]
        dec_deg = float_cells[-1]

        observations.append(
            Observation(
                t=t_str,
                ra_deg=ra_deg,
                dec_deg=dec_deg,
            )
        )

    if not observations:
        raise ValueError("Parsed 0 observations. Horizons format might differ — we’ll adjust parsing.")

    return observations


def save_observations_json(observations: List[Observation], out_path: str) -> None:
    data = [obs.__dict__ for obs in observations]
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
