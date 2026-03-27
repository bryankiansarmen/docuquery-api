from pydantic import BaseModel
from typing import Optional

class Question(BaseModel):
    message: str
    document_id: str
    session_id: Optional[str] = None