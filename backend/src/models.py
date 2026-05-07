from pydantic import BaseModel
from typing import Optional, List

class ProcessRequest(BaseModel):
    style: str  # e.g. "Picasso", "Van Gogh"
    image_url: Optional[str] = None  # Cloud Storage URL

class Coordinate(BaseModel):
    x: float
    y: float

class ProcessResponse(BaseModel):
    status: str
    style: str
    coordinates: List[Coordinate]
    image_url: Optional[str] = None
    message: Optional[str] = None

class UploadResponse(BaseModel):
    status: str
    image_url: str
    filename: str

class HealthResponse(BaseModel):
    status: str
    project_id: str
    version: str