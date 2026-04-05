from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.routes.users_router import router as users_router
from backend.routes.observations_router import router as observations_router

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"message": "AsteroidTrack API running"}

app.include_router(users_router)
app.include_router(observations_router)