# app/schemas/auth_schema.py

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field

# ---------- Inputs ----------

class UserCreate(BaseModel):
    email: EmailStr
    # mínimo 8 chars e limite superior para evitar payload gigante
    password: str = Field(min_length=8, max_length=128)
    # opcional, mas com tamanho razoável
    nome: Optional[str] = Field(default=None, max_length=255)

    model_config = {"from_attributes": True}


class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)  # no login basta não ser vazio

    model_config = {"from_attributes": True}


# ---------- Outputs (para resposta) ----------

class UserResponse(BaseModel):
    id: int
    email: EmailStr
    nome: Optional[str] = None
    is_active: bool
    is_verified: bool
    created_at: datetime
    # útil no dashboard; se não quiser expor agora, remova:
    # last_login: Optional[datetime] = None

    model_config = {"from_attributes": True}


class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse

    model_config = {"from_attributes": True}


# Usado no decode do JWT (mantendo compatibilidade: sub = email)
class TokenData(BaseModel):
    email: Optional[str] = None

    model_config = {"from_attributes": True}
