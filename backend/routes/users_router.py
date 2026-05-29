from fastapi import APIRouter, Header
from backend.db.mongo import users_collection
from backend.utils.security import hash_password, verify_password
from backend.utils.jwt_utils import (
    create_access_token,
    create_refresh_token,
    verify_token,
)

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

    token_data = {
        "sub": existing_user["username"],
        "email": existing_user["email"],
    }

    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    return {
        "message": "Login successful",
        "username": existing_user["username"],
        "email": existing_user["email"],
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


@router.post("/refresh")
def refresh_access_token(data: dict):
    refresh_token = data.get("refresh_token")

    if not refresh_token:
        return {"message": "Refresh token is required"}

    payload = verify_token(refresh_token)

    if not payload:
        return {"message": "Invalid or expired refresh token"}

    if payload.get("type") != "refresh":
        return {"message": "Invalid token type"}

    username = payload.get("sub")
    email = payload.get("email")

    if not username:
        return {"message": "Invalid token payload"}

    new_access_token = create_access_token({
        "sub": username,
        "email": email,
    })

    return {
        "message": "Token refreshed successfully",
        "access_token": new_access_token,
        "token_type": "bearer",
    }


@router.get("/me")
def get_current_user(authorization: str = Header(default="")):
    if not authorization.startswith("Bearer "):
        return {"message": "Missing or invalid authorization header"}

    token = authorization.replace("Bearer ", "")
    payload = verify_token(token)

    if not payload:
        return {"message": "Invalid or expired token"}

    if payload.get("type") != "access":
        return {"message": "Invalid token type"}

    return {
        "username": payload.get("sub"),
        "email": payload.get("email"),
    }