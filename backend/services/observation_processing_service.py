from datetime import datetime


MIN_OBSERVATIONS_COUNT = 6


def process_observations_data(data):
    if not isinstance(data, list):
        return False, None, {
            "message": "Observation data must be a list",
            "status": "ProcessingFailed"
        }

    if len(data) < MIN_OBSERVATIONS_COUNT:
        return False, None, {
            "message": f"At least {MIN_OBSERVATIONS_COUNT} observations are required",
            "status": "ProcessingFailed",
            "count": len(data)
        }

    seen_times = set()
    processed_data = []
    duplicates_count = 0

    for index, observation in enumerate(data):
        time_value = observation.get("time")
        ra = observation.get("ra")
        dec = observation.get("dec")

        if time_value in seen_times:
            duplicates_count += 1
            continue

        seen_times.add(time_value)

        if not (0 <= ra <= 360):
            return False, None, {
                "message": f"Observation #{index + 1} has invalid RA value",
                "status": "ProcessingFailed",
                "invalidField": "ra"
            }

        if not (-90 <= dec <= 90):
            return False, None, {
                "message": f"Observation #{index + 1} has invalid DEC value",
                "status": "ProcessingFailed",
                "invalidField": "dec"
            }

        processed_data.append({
            "time": time_value,
            "ra": ra,
            "dec": dec
        })

    processed_data.sort(key=lambda item: item["time"])

    if len(processed_data) < MIN_OBSERVATIONS_COUNT:
        return False, None, {
            "message": "Not enough observations after removing duplicates",
            "status": "ProcessingFailed",
            "countAfterProcessing": len(processed_data)
        }

    summary = {
        "message": "Observation set processed successfully",
        "status": "ReadyForOrbitCalculation",
        "originalCount": len(data),
        "processedCount": len(processed_data),
        "duplicatesRemoved": duplicates_count,
        "processedAt": datetime.utcnow().isoformat()
    }

    return True, processed_data, summary