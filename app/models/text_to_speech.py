from pydantic import BaseModel
from typing import Optional

class TTSRequest(BaseModel):
    text: str
