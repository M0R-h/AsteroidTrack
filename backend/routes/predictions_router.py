from fastapi import APIRouter
from bson import ObjectId
from datetime import datetime

from backend.db.mongo import orbital_elements_collection, predictions_collection
from backend.services.prediction_service import generate_predictions

router = APIRouter()


@router.post("/orbital-elements/{element_id}/predict")
def predict_orbit(element_id: str):

    if not ObjectId.is_valid(element_id):
        return {"message": "Invalid element id"}

    element = orbital_elements_collection.find_one(
        {"_id": ObjectId(element_id)}
    )

    if not element:
        return {"message": "Orbital element not found"}

    orbital_elements = element["orbitalElements"]

    predictions = generate_predictions(orbital_elements)

    doc = {
        "orbitalElementId": element_id,
        "createdAt": datetime.utcnow().isoformat(),
        "count": len(predictions),
        "data": predictions
    }

    result = predictions_collection.insert_one(doc)

    return {
        "message": "Predictions generated",
        "predictionId": str(result.inserted_id),
        "count": len(predictions)
    }

@router.get("/predictions/by-orbital-element/{orbital_element_id}")
def get_predictions_by_orbital_element(orbital_element_id: str):
    prediction = predictions_collection.find_one(
        {"orbitalElementId": orbital_element_id},
        {"_id": 0}
    )

    if not prediction:
        return {
            "message": "No predictions found for this orbital element",
            "orbitalElementId": orbital_element_id,
            "data": []
        }

    return prediction