from pydantic import BaseModel, EmailStr, Field
from datetime import datetime, timezone
from typing import Optional

class User(BaseModel):
    id: Optional[str] = Field(alias="_id")
    name: str
    email: EmailStr
    password: Optional[str] = None
    provider: str = "local"  # local, google, github
    role: str = "tester"     # admin, lead, tester
    created_at: datetime = datetime.now(timezone.utc)

    # allows using 'id=' instead of '_id'
    class Config:
        populate_by_name = True 
