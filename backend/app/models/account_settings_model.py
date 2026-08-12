from datetime import datetime
from enum import StrEnum
from sqlalchemy import (
    Column, Integer, String, DateTime, Enum, ForeignKey,
    UniqueConstraint, Index
)
from sqlalchemy.sql import func
from app.database.database import Base  # mesmo Base do seu User

class PersonType(StrEnum):
    PF = "PF"
    PJ = "PJ"

class AccountSettings(Base):
    __tablename__ = "account_settings"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_account_settings_user"),
        Index("ix_account_settings_updated_at", "updated_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    # 1-para-1 com users.id
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)

    person_type = Column(Enum(PersonType), nullable=False, default=PersonType.PF)
    display_name = Column(String(120), nullable=False)

    niche = Column(String(120), nullable=True)
    bio = Column(String(500), nullable=True)

    # endereço (MVP)
    street = Column(String(120), nullable=True)
    number = Column(String(20), nullable=True)
    city = Column(String(80), nullable=True)
    state = Column(String(40), nullable=True)
    zip_code = Column(String(20), nullable=True)

    # url da foto/logo (S3/CDN/etc.)
    media_url = Column(String(400), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self) -> str:
        return f"<AccountSettings user_id={self.user_id} type={self.person_type} name={self.display_name!r}>"
