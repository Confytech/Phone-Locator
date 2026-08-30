from datetime import datetime

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import Base, SessionLocal, engine
from models import Location


# Create database tables
Base.metadata.create_all(bind=engine)


app = FastAPI(
    title="My Phone Locator",
    description="API for receiving and retrieving phone GPS locations.",
    version="1.0.0"
)


# --------------------------------------------------
# Temporary authentication
# --------------------------------------------------

DEVICE_API_KEY = "my-phone-secret-key"


# --------------------------------------------------
# Location request model
# --------------------------------------------------

class LocationData(BaseModel):
    device_id: str
    latitude: float
    longitude: float
    accuracy: float | None = None


# --------------------------------------------------
# Home
# --------------------------------------------------

@app.get("/")
def home():
    return {
        "status": "online",
        "message": "My Phone Locator API is running"
    }


# --------------------------------------------------
# Send phone location
# --------------------------------------------------

@app.post("/location")
def receive_location(
    data: LocationData,
    x_api_key: str | None = Header(default=None)
):

    # Check authentication
    if x_api_key != DEVICE_API_KEY:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key"
        )

    db: Session = SessionLocal()

    try:

        location = Location(
            device_id=data.device_id,
            latitude=data.latitude,
            longitude=data.longitude,
            accuracy=data.accuracy,
            timestamp=datetime.utcnow()
        )

        db.add(location)
        db.commit()
        db.refresh(location)

        return {
            "success": True,
            "message": "Location received",
            "location": {
                "id": location.id,
                "device_id": location.device_id,
                "latitude": location.latitude,
                "longitude": location.longitude,
                "accuracy": location.accuracy,
                "timestamp": location.timestamp
            }
        }

    finally:
        db.close()


# --------------------------------------------------
# Get latest location
# --------------------------------------------------

@app.get("/location/latest/{device_id}")
def get_latest_location(
    device_id: str,
    x_api_key: str | None = Header(default=None)
):

    # Check authentication
    if x_api_key != DEVICE_API_KEY:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key"
        )

    db: Session = SessionLocal()

    try:

        location = (
            db.query(Location)
            .filter(Location.device_id == device_id)
            .order_by(Location.timestamp.desc())
            .first()
        )

        if location is None:
            raise HTTPException(
                status_code=404,
                detail="No location found for this device"
            )

        return {
            "device_id": location.device_id,
            "latitude": location.latitude,
            "longitude": location.longitude,
            "accuracy": location.accuracy,
            "timestamp": location.timestamp
        }

    finally:
        db.close()