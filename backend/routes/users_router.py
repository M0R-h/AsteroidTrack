from fastapi import APIRouter
from backend.db.mongo import users_collection
from backend.utils.security import hash_password, verify_password

router = APIRouter()


@router.post("/register")
def register_user(user: dict):
    existing_user_by_username = users_collection.find_one({"username": user["username"]})
    if existing_user_by_username:
        return {"message": "Username already exists"}

    existing_user_by_email = users_collection.find_one({"email": user["email"]})
    if existing_user_by_email:
        return {"message": "Email already exists"}

    hashed_password = hash_password(user["password"])

    users_collection.insert_one(
        {
            "username": user["username"],
            "email": user["email"],
            "password": hashed_password,
        }
    )

    return {"message": "User created successfully"}


@router.post("/login")
def login_user(user: dict):
    existing_user = users_collection.find_one({"username": user["username"]})

    if not existing_user:
        return {"message": "Invalid username or password"}

    if not verify_password(user["password"], existing_user["password"]):
        return {"message": "Invalid username or password"}

    return {
        "message": "Login successful",
        "username": existing_user["username"],
        "email": existing_user["email"],
    }