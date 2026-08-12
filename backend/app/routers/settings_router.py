# app/routers/settings_router.py
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from starlette.status import HTTP_404_NOT_FOUND
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.dependencies.auth import get_current_active_user  # o mesmo usado no seu auth_router.py

from app.schemas.auth_schema import UserResponse  # já usado nas suas rotas /me
from app.schemas.settings_schema import SettingsCreate, SettingsUpdate, SettingsOut
from app.services.settings_service import SettingsService

router = APIRouter(prefix="/settings", tags=["settings"])

@router.get("/me", response_model=SettingsOut)
def get_my_settings(
    current_user: UserResponse = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    entity = SettingsService.get_by_user(db, current_user.id)
    if not entity:
        raise HTTPException(HTTP_404_NOT_FOUND, detail="Configurações não encontradas")
    return entity

@router.put("/me", response_model=SettingsOut)
def save_my_settings(
    body: dict,  # cliente NÃO envia user_id; vem do token
    current_user: UserResponse = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    PUT completo SEM user_id no body.
    """
    payload = SettingsCreate(user_id=current_user.id, **body)
    return SettingsService.upsert(db, payload)

@router.patch("/me", response_model=SettingsOut)
def patch_my_settings(
    patch: SettingsUpdate,
    current_user: UserResponse = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    return SettingsService.patch(db, current_user.id, patch)

@router.post("/me/media", response_model=dict)
def upload_media(
    file: UploadFile = File(...),
    current_user: UserResponse = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    if file.content_type not in {"image/png", "image/jpeg", "image/webp"}:
        raise HTTPException(status_code=415, detail="Formato de imagem inválido")
    # Integre com seu storage/CDN e gere URL pública real:
    url = f"https://cdn.seuservico.com/users/{current_user.id}/{file.filename}"
    SettingsService.patch(db, current_user.id, SettingsUpdate(media_url=url))
    return {"url": url}
