from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import sensor, alerts

app = FastAPI(title="SchoolShield API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(sensor.router)
app.include_router(alerts.router)

@app.get("/")
def root():
    return {"status": "SchoolShield API running"}
