from pydantic import BaseModel
from typing import Optional, List

class ProcessRequest(BaseModel):
    style: str  # e.g. "Picasso", "Van Gogh"
    image_url: Optional[str] = None  # Cloud Storage URL

class Coordinate(BaseModel):
    x: float
    y: float

class Dimensions(BaseModel):
    width: int
    height: int

class ProcessResponse(BaseModel):
    status: str
    style: str
    coordinates: List[Coordinate]
    image_url: Optional[str] = None
    styled_image_url: Optional[str] = None
    transcript: Optional[str] = None
    message: Optional[str] = None
    svg: Optional[str] = None
    dimensions: Optional[Dimensions] = None

class UploadResponse(BaseModel):
    status: str
    image_url: str
    filename: str

class HealthResponse(BaseModel):
    status: str
    project_id: str
    version: str