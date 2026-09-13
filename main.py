import os
from datetime import datetime

import requests
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
    version="1.1.0"
)


# --------------------------------------------------
# API authentication
# --------------------------------------------------

# Railway will provide DEVICE_API_KEY as an environment variable.
# The fallback keeps local development working for now.
DEVICE_API_KEY = os.getenv(
    "DEVICE_API_KEY",
    "my-phone-secret-key"
)


# --------------------------------------------------
# Location request model
# --------------------------------------------------

class LocationData(BaseModel):
    device_id: str
    latitude: float
    longitude: float
    accuracy: float | None = None


# --------------------------------------------------
# Reverse geocoding
# --------------------------------------------------

def get_location_name(latitude: float, longitude: float):

    url = "https://nominatim.openstreetmap.org/reverse"

    params = {
        "lat": latitude,
        "lon": longitude,
        "format": "jsonv2",
        "addressdetails": 1,
        "zoom": 18
    }

    headers = {
        "User-Agent": "MyPhoneLocator/1.0"
    }

    try:
        response = requests.get(
            url,
            params=params,
            headers=headers,
            timeout=10
        )

        response.raise_for_status()

        data = response.json()

        return {
            "display_name": data.get("display_name"),
            "address": data.get("address", {})
        }

    except requests.RequestException:
        return {
            "display_name": None,
            "address": {}
        }


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

        # Get human-readable location
        location_info = get_location_name(
            data.latitude,
            data.longitude
        )

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
                "timestamp": location.timestamp,

                "place": location_info["display_name"],
                "address": location_info["address"]
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

        # Reverse geocode latest location
        location_info = get_location_name(
            location.latitude,
            location.longitude
        )

        return {
            "device_id": location.device_id,
            "latitude": location.latitude,
            "longitude": location.longitude,
            "accuracy": location.accuracy,
            "timestamp": location.timestamp,

            "place": location_info["display_name"],
            "address": location_info["address"]
        }

    finally:
        db.close()