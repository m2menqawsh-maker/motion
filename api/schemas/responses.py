from pydantic import BaseModel
from typing import Any, Optional, Dict

class StandardResponse(BaseModel):
    status: str = "success"
    message: Optional[str] = None
    data: Optional[Dict[str, Any]] = None

class ErrorResponse(BaseModel):
    status: str = "error"
    error: str
    message: str
    details: Optional[Dict[str, Any]] = None
