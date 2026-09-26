from pydantic import BaseModel
from typing import Optional, Dict, Any

class BlueprintResponse(BaseModel):
    blueprint: Optional[Dict[str, Any]] = None
    overrides: Optional[Dict[str, Any]] = None
