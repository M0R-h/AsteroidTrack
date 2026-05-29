from fastapi import APIRouter, UploadFile, File, Form
from backend.db.mongo import (
    observations_collection,
    orbital_elements_collection,
    processing_logs_collection,
    predictions_collection,
)
from backend.services.observation_processing_service import process_observations_data
from backend.services.prediction_service import generate_predictions
from core.optimizer_lm import fit_orbit
from bson import ObjectId
from datetime import datetime, timedelta
import json

router = APIRouter()


def serialize_observation(document):
    document["id"] = str(document["_id"])
    document.pop("_id", None)
    return document


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
        observations_collection.find({"uploadedBy": username}).sort("uploadedAt", -1)
    )
    return [serialize_observation(obs) for obs in observations]


@router.get("/observations/public")
def get_public_observations():
    observations = list(
        observations_collection.find({"visibility": "public"}).sort("uploadedAt", -1)
    )
    return [serialize_observation(obs) for obs in observations]


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
        "processedData": [],
        "processingSummary": None,
        "processedAt": None,
    }

    result = observations_collection.insert_one(document)
    observation_id = str(result.inserted_id)

    if is_valid:
        return {
            "message": "File uploaded and validated successfully",
            "id": observation_id,
            "fileName": file.filename,
            "uploadedBy": uploadedBy,
            "count": len(parsed_data),
            "status": "Validated",
            "visibility": visibility,
        }

    return {
        "message": "File uploaded but failed validation",
        "id": observation_id,
        "fileName": file.filename,
        "uploadedBy": uploadedBy,
        "count": len(parsed_data) if isinstance(parsed_data, list) else 0,
        "status": "Invalid",
        "invalidReason": invalid_reason,
        "visibility": visibility,
    }


@router.post("/observations/{observation_id}/process")
def process_observation_set(observation_id: str):
    if not ObjectId.is_valid(observation_id):
        return {"message": "Invalid observation id"}

    observation_set = observations_collection.find_one(
        {"_id": ObjectId(observation_id)}
    )

    if observation_set is None:
        return {"message": "Observation set not found"}

    if observation_set.get("status") == "Invalid":
        return {
            "message": "Cannot process invalid observation file",
            "invalidReason": observation_set.get("invalidReason", ""),
        }

    data = observation_set.get("data", [])
    success, processed_data, summary = process_observations_data(data)

    if not success:
        observations_collection.update_one(
            {"_id": ObjectId(observation_id)},
            {
                "$set": {
                    "status": "ProcessingFailed",
                    "processingSummary": summary,
                    "processedAt": datetime.utcnow().isoformat(),
                }
            },
        )
        return summary

    observations_collection.update_one(
        {"_id": ObjectId(observation_id)},
        {
            "$set": {
                "status": "ReadyForOrbitCalculation",
                "processedData": processed_data,
                "processingSummary": summary,
                "processedAt": summary["processedAt"],
            }
        },
    )

    return {
        "message": "Observation set is ready for orbit calculation",
        "id": observation_id,
        "status": "ReadyForOrbitCalculation",
        "summary": summary,
    }


@router.post("/observations/{observation_id}/fit-orbit")
def fit_orbit_for_observation_set(observation_id: str):
    if not ObjectId.is_valid(observation_id):
        return {"message": "Invalid observation id"}

    observation_set = observations_collection.find_one(
        {"_id": ObjectId(observation_id)}
    )

    if observation_set is None:
        return {"message": "Observation set not found"}

    if observation_set.get("status") != "ReadyForOrbitCalculation":
        return {
            "message": "Observation set is not ready for orbit calculation",
            "currentStatus": observation_set.get("status"),
        }

    processed_data = observation_set.get("processedData", [])

    if not processed_data:
        return {"message": "No processed data found"}

    started_at = datetime.utcnow().isoformat()

    try:
        result = fit_orbit(processed_data)

        orbital_document = {
            "observationSetId": observation_id,
            "uploadedBy": observation_set.get("uploadedBy"),
            "fileName": observation_set.get("fileName"),
            "calculatedAt": datetime.utcnow().isoformat(),
            "algorithm": "Custom Iterative Orbit Fitting",
            "orbitalElements": result["best_params"],
            "rmsDeg": result["best_rms_deg"],
            "observationsCount": len(processed_data),
            "status": "Success",
        }

        insert_result = orbital_elements_collection.insert_one(orbital_document)
        orbital_element_id = str(insert_result.inserted_id)

        observations_collection.update_one(
            {"_id": ObjectId(observation_id)},
            {
                "$set": {
                    "status": "OrbitCalculated",
                    "orbitalElementId": orbital_element_id,
                    "orbitCalculatedAt": datetime.utcnow().isoformat(),
                }
            },
        )

        processing_logs_collection.insert_one({
            "operation": "Orbit Determination",
            "observationSetId": observation_id,
            "orbitalElementId": orbital_element_id,
            "startedAt": started_at,
            "finishedAt": datetime.utcnow().isoformat(),
            "status": "Success",
            "observationsCount": len(processed_data),
            "rmsDeg": result["best_rms_deg"],
            "message": "Orbit fitting completed successfully",
        })

        return {
            "message": "Orbit calculated successfully",
            "observationSetId": observation_id,
            "orbitalElementId": orbital_element_id,
            "rmsDeg": result["best_rms_deg"],
            "orbitalElements": result["best_params"],
        }

    except Exception as error:
        processing_logs_collection.insert_one({
            "operation": "Orbit Determination",
            "observationSetId": observation_id,
            "startedAt": started_at,
            "finishedAt": datetime.utcnow().isoformat(),
            "status": "Failed",
            "error": str(error),
            "message": "Orbit fitting failed",
        })

        return {
            "message": "Orbit fitting failed",
            "error": str(error),
        }
    
def parse_prediction_start_time(time_str: str) -> datetime:
    try:
        return datetime.fromisoformat(time_str)
    except ValueError:
        pass

    parts = time_str.split()
    if len(parts) >= 2:
        base_time = " ".join(parts[:2])
        return datetime.strptime(base_time, "%Y-%b-%d %H:%M")

    raise ValueError(f"Unsupported time format: {time_str}")

def datetime_to_jd(dt: datetime) -> float:
    year = dt.year
    month = dt.month
    day = dt.day + (
        dt.hour / 24
        + dt.minute / 1440
        + dt.second / 86400
        + dt.microsecond / 86400000000
    )

    if month <= 2:
        year -= 1
        month += 12

    A = year // 100
    B = 2 - A + (A // 4)

    jd = int(365.25 * (year + 4716)) + int(30.6001 * (month + 1)) + day + B - 1524.5
    return jd


def extract_jd_from_time(time_str: str) -> float:
    parts = time_str.split()

    if len(parts) >= 3:
        return float(parts[2])

    dt = parse_prediction_start_time(time_str)
    return datetime_to_jd(dt)


@router.post("/observations/{observation_id}/analyze")
def analyze_observation_set(observation_id: str):
    if not ObjectId.is_valid(observation_id):
        return {"message": "Invalid observation id"}

    observation_set = observations_collection.find_one(
        {"_id": ObjectId(observation_id)}
    )

    if observation_set is None:
        return {"message": "Observation set not found"}

    if observation_set.get("status") == "Invalid":
        return {
            "message": "Cannot analyze invalid observation file",
            "invalidReason": observation_set.get("invalidReason", ""),
        }

    if observation_set.get("status") == "OrbitCalculated":
        return {
            "message": "Observation already analyzed",
            "observationSetId": observation_id,
            "orbitalElementId": observation_set.get("orbitalElementId"),
            "status": "OrbitCalculated",
        }

    started_at = datetime.utcnow().isoformat()

    try:
        data = observation_set.get("data", [])

        success, processed_data, summary = process_observations_data(data)

        if not success:
            observations_collection.update_one(
                {"_id": ObjectId(observation_id)},
                {
                    "$set": {
                        "status": "ProcessingFailed",
                        "processingSummary": summary,
                        "processedAt": datetime.utcnow().isoformat(),
                    }
                },
            )
            return summary

        observations_collection.update_one(
            {"_id": ObjectId(observation_id)},
            {
                "$set": {
                    "status": "ReadyForOrbitCalculation",
                    "processedData": processed_data,
                    "processingSummary": summary,
                    "processedAt": summary["processedAt"],
                }
            },
        )

        result = fit_orbit(processed_data)

        orbital_document = {
            "observationSetId": observation_id,
            "uploadedBy": observation_set.get("uploadedBy"),
            "fileName": observation_set.get("fileName"),
            "calculatedAt": datetime.utcnow().isoformat(),
            "algorithm": "Custom Iterative Orbit Fitting + Outlier Weighting",
            "orbitalElements": result["best_params"],
            "rmsDeg": result["best_rms_deg"],
            "weightedRmsDeg": result["weighted_rms_deg"],
            "outlierCount": result["outlier_count"],
            "observationsCount": len(processed_data),
            "status": "Success",
        }

        insert_result = orbital_elements_collection.insert_one(orbital_document)
        orbital_element_id = str(insert_result.inserted_id)

        last_time_str = processed_data[-1]["time"]
        prediction_start_time = parse_prediction_start_time(last_time_str) + timedelta(days=1)
        last_jd = extract_jd_from_time(processed_data[-1]["time"])
        prediction_start_jd = last_jd + 1
        
        predictions = generate_predictions(
            result["best_params"],
            start_time=prediction_start_time,
            start_jd=prediction_start_jd
            )

        prediction_document = {
            "orbitalElementId": orbital_element_id,
            "createdAt": datetime.utcnow().isoformat(),
            "count": len(predictions),
            "data": predictions,
        }

        prediction_result = predictions_collection.insert_one(prediction_document)

        observations_collection.update_one(
            {"_id": ObjectId(observation_id)},
            {
                "$set": {
                    "status": "OrbitCalculated",
                    "orbitalElementId": orbital_element_id,
                    "orbitCalculatedAt": datetime.utcnow().isoformat(),
                }
            },
        )

        processing_logs_collection.insert_one({
            "operation": "Full Analysis",
            "observationSetId": observation_id,
            "orbitalElementId": orbital_element_id,
            "predictionId": str(prediction_result.inserted_id),
            "startedAt": started_at,
            "finishedAt": datetime.utcnow().isoformat(),
            "status": "Success",
            "observationsCount": len(processed_data),
            "rmsDeg": result["best_rms_deg"],
            "weightedRmsDeg": result["weighted_rms_deg"],
            "outlierCount": result["outlier_count"],
            "message": "Full analysis completed successfully with outlier weighting",
        })

        return {
            "message": "Analysis completed successfully",
            "observationSetId": observation_id,
            "orbitalElementId": orbital_element_id,
            "predictionId": str(prediction_result.inserted_id),
            "status": "OrbitCalculated",
            "rmsDeg": result["best_rms_deg"],
            "weightedRmsDeg": result["weighted_rms_deg"],
            "outlierCount": result["outlier_count"],
            "orbitalElements": result["best_params"],
        }

    except Exception as error:
        processing_logs_collection.insert_one({
            "operation": "Full Analysis",
            "observationSetId": observation_id,
            "startedAt": started_at,
            "finishedAt": datetime.utcnow().isoformat(),
            "status": "Failed",
            "error": str(error),
            "message": "Full analysis failed",
        })

        return {
            "message": "Analysis failed",
            "error": str(error),
        }


@router.delete("/observations/{observation_id}")
def delete_observation_set(observation_id: str):
    if not ObjectId.is_valid(observation_id):
        return {"message": "Invalid observation id"}

    observation_set = observations_collection.find_one(
        {"_id": ObjectId(observation_id)}
    )

    if observation_set is None:
        return {"message": "Observation set not found"}

    orbital_elements = list(
        orbital_elements_collection.find(
            {"observationSetId": observation_id},
            {"_id": 1}
        )
    )

    orbital_element_ids = [str(item["_id"]) for item in orbital_elements]

    if orbital_element_ids:
        predictions_collection.delete_many(
            {"orbitalElementId": {"$in": orbital_element_ids}}
        )

        orbital_elements_collection.delete_many(
            {"observationSetId": observation_id}
        )

    observations_collection.delete_one(
        {"_id": ObjectId(observation_id)}
    )

    processing_logs_collection.insert_one({
        "operation": "Delete Observation",
        "observationSetId": observation_id,
        "deletedOrbitalElements": orbital_element_ids,
        "deletedAt": datetime.utcnow().isoformat(),
        "status": "Success",
        "message": "Observation and related results were deleted",
    })

    return {
        "message": "Observation deleted successfully",
        "observationSetId": observation_id,
        "deletedOrbitalElements": len(orbital_element_ids),
    }

def parse_prediction_start_time(time_str: str) -> datetime:
    try:
        return datetime.fromisoformat(time_str)
    except ValueError:
        pass

    parts = time_str.split()
    if len(parts) >= 2:
        base_time = " ".join(parts[:2])
        return datetime.strptime(base_time, "%Y-%b-%d %H:%M")

    raise ValueError(f"Unsupported time format: {time_str}")