# app/services/settings_service.py
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models.account_settings_model import AccountSettings, PersonType
from app.schemas.settings_schema import SettingsCreate, SettingsUpdate

class SettingsService:
    @staticmethod
    def get_by_user(db: Session, user_id: int) -> AccountSettings | None:
        stmt = select(AccountSettings).where(AccountSettings.user_id == user_id)
        return db.execute(stmt).scalar_one_or_none()

    @staticmethod
    def upsert(db: Session, data: SettingsCreate) -> AccountSettings:
        entity = SettingsService.get_by_user(db, data.user_id)
        if entity is None:
            entity = AccountSettings(
                user_id=data.user_id,
                person_type=PersonType(data.person_type),
                display_name=data.display_name,
                niche=data.niche,
                bio=data.bio,
                street=data.street,
                number=data.number,
                city=data.city,
                state=data.state,
                zip_code=data.zip_code,
                media_url=data.media_url,
            )
            db.add(entity)
        else:
            entity.person_type = PersonType(data.person_type)
            entity.display_name = data.display_name
            entity.niche = data.niche
            entity.bio = data.bio
            entity.street = data.street
            entity.number = data.number
            entity.city = data.city
            entity.state = data.state
            entity.zip_code = data.zip_code
            entity.media_url = data.media_url
            entity.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(entity)
        return entity

    @staticmethod
    def patch(db: Session, user_id: int, patch: SettingsUpdate) -> AccountSettings:
        entity = SettingsService.get_by_user(db, user_id)
        if entity is None:
            # cria com mínimos
            payload = SettingsCreate(
                user_id=user_id,
                person_type=patch.person_type or "PF",
                display_name=patch.display_name or "Novo(a)",
                niche=patch.niche, bio=patch.bio,
                street=patch.street, number=patch.number, city=patch.city,
                state=patch.state, zip_code=patch.zip_code,
                media_url=patch.media_url,
            )
            return SettingsService.upsert(db, payload)

        data = patch.model_dump(exclude_unset=True)
        if "person_type" in data:
            entity.person_type = PersonType(data.pop("person_type"))
        for k, v in data.items():
            setattr(entity, k, v)
        entity.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(entity)
        return entity
