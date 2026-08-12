from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, Field, HttpUrl, constr
from pydantic import ConfigDict

PersonTypeLiteral = Literal["PF", "PJ"]

class SettingsBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    person_type: PersonTypeLiteral = Field(default="PF")
    display_name: constr(strip_whitespace=True, min_length=2, max_length=120)

    niche: Optional[constr(strip_whitespace=True, max_length=120)] = None
    bio: Optional[constr(strip_whitespace=True, max_length=500)] = None

    street: Optional[str] = None
    number: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None

    media_url: Optional[HttpUrl | str] = None

class SettingsCreate(SettingsBase):
    user_id: int

class SettingsUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    person_type: Optional[PersonTypeLiteral] = None
    display_name: Optional[constr(strip_whitespace=True, min_length=2, max_length=120)] = None
    niche: Optional[str] = None
    bio: Optional[str] = None
    street: Optional[str] = None
    number: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    media_url: Optional[HttpUrl | str] = None

class SettingsOut(SettingsBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime
