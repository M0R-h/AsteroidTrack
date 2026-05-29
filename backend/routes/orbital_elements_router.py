from fastapi import APIRouter
from bson import ObjectId

from backend.db.mongo import orbital_elements_collection

router = APIRouter()


def serialize_orbital_element(document):
    document["id"] = str(document["_id"])
    document.pop("_id", None)
    return document


@router.get("/orbital-elements/{element_id}")
def get_orbital_element(element_id: str):
    if not ObjectId.is_valid(element_id):
        return {"message": "Invalid orbital element id"}

    element = orbital_elements_collection.find_one(
        {"_id": ObjectId(element_id)}
    )

    if not element:
        return {"message": "Orbital element not found"}

    return serialize_orbital_element(element)