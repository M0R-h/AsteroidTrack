from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.routes.users_router import router as users_router
from backend.routes.observations_router import router as observations_router
from backend.routes.predictions_router import router as predictions_router
from backend.routes.orbital_elements_router import router as orbital_elements_router

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"message": "AsteroidTrack API running"}

app.include_router(users_router)
app.include_router(observations_router)
app.include_router(predictions_router)
app.include_router(orbital_elements_router)