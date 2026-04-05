from fastapi import APIRouter, UploadFile, File, Form
from backend.db.mongo import observations_collection
from datetime import datetime
import json

router = APIRouter()


def validate_observations(data):
    if not isinstance(data, list):
        return False, "JSON file must contain a list of observations"

    if len(data) == 0:
        return False, "Observation file is empty"

    for index, item in enumerate(data):
        if not isinstance(item, dict):
            return False, f"Observation #{index + 1} must be an object"

        required_fields = ["time", "ra", "dec"]
        for field in required_fields:
            if field not in item:
                return False, f"Observation #{index + 1} is missing '{field}'"

        if not isinstance(item["time"], str):
            return False, f"Observation #{index + 1} field 'time' must be a string"

        if not isinstance(item["ra"], (int, float)):
            return False, f"Observation #{index + 1} field 'ra' must be a number"

        if not isinstance(item["dec"], (int, float)):
            return False, f"Observation #{index + 1} field 'dec' must be a number"

    return True, ""


@router.get("/observations/my/{username}")
def get_my_observations(username: str):
    observations = list(
        observations_collection.find(
            {"uploadedBy": username},
            {"_id": 0}
        ).sort("uploadedAt", -1)
    )
    return observations


@router.get("/observations/public")
def get_public_observations():
    observations = list(
        observations_collection.find(
            {"visibility": "public"},
            {"_id": 0}
        ).sort("uploadedAt", -1)
    )
    return observations


@router.post("/observations/upload")
async def upload_observations(
    file: UploadFile = File(...),
    uploadedBy: str = Form(...),
    visibility: str = Form("private")
):
    if visibility not in ["private", "public"]:
        return {"message": "Visibility must be either 'private' or 'public'"}

    if not file.filename.endswith(".json"):
        return {"message": "Only JSON files are supported for now"}

    content = await file.read()

    try:
        parsed_data = json.loads(content.decode("utf-8"))
    except Exception:
        return {"message": "Invalid JSON file"}

    is_valid, invalid_reason = validate_observations(parsed_data)

    document = {
        "fileName": file.filename,
        "uploadedBy": uploadedBy,
        "uploadedAt": datetime.utcnow().isoformat(),
        "count": len(parsed_data) if isinstance(parsed_data, list) else 0,
        "status": "Validated" if is_valid else "Invalid",
        "invalidReason": invalid_reason if not is_valid else "",
        "visibility": visibility,
        "data": parsed_data,
    }

    observations_collection.insert_one(document)

    if is_valid:
        return {
            "message": "File uploaded and validated successfully",
            "fileName": file.filename,
            "uploadedBy": uploadedBy,
            "count": len(parsed_data),
            "status": "Validated",
            "visibility": visibility,
        }

    return {
        "message": "File uploaded but failed validation",
        "fileName": file.filename,
        "uploadedBy": uploadedBy,
        "count": len(parsed_data) if isinstance(parsed_data, list) else 0,
        "status": "Invalid",
        "invalidReason": invalid_reason,
        "visibility": visibility,
    }