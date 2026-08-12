# app/models/user_model.py

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Index
from sqlalchemy.orm import validates
from sqlalchemy.sql import func
from app.database.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    # 320 é o limite teórico de e-mail. Index + unique já existiam; mantidos.
    email = Column(String(320), unique=True, index=True, nullable=False)

    # bcrypt gera ~60 chars; deixo folga (128) para futuros algoritmos.
    hashed_password = Column(String(128), nullable=False)

    # Nome opcional com limite razoável
    nome = Column(String(255), nullable=True)

    is_active = Column(Boolean, nullable=False, default=True)
    is_verified = Column(Boolean, nullable=False, default=False)

    # timezone-aware (depende do driver). server_default = now() no banco.
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_login = Column(DateTime(timezone=True), nullable=True)

    # Índices extras úteis para dashboards (ordenar por criação / últimos logins)
    __table_args__ = (
        Index("ix_users_created_at", created_at.desc()),
        Index("ix_users_last_login", last_login.desc()),
    )

    # Normaliza email no set/insert/update
    @validates("email")
    def _normalize_email(self, key, value: str):
        if value is None:
            return value
        return value.strip().lower()

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email!r} active={self.is_active}>"

    class Config:
        from_attributes = True
