# app/dependencies/auth.py

from __future__ import annotations

from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from ..database.database import get_db
from ..services.auth_service import AuthService
from ..models.user_model import User

# Se auto_error=True, o FastAPI levanta 403 quando o header está ausente,
# o que não é ideal para fluxos Bearer. Usamos False para controlar a resposta (401).
security = HTTPBearer(auto_error=False)

unauthorized_exc = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Token inválido ou ausente",
    headers={"WWW-Authenticate": "Bearer"},
)

def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """
    Lê o header Authorization: Bearer <token>, valida o JWT e retorna o usuário ativo no banco.
    Mantém compatibilidade: AuthService.verify_token espera sub=email (sem expiração).
    """
    # Header ausente ou malformado
    if not credentials or not credentials.credentials:
        raise unauthorized_exc

    # Esquema deve ser 'Bearer'
    if (credentials.scheme or "").lower() != "bearer":
        raise unauthorized_exc

    # Decodifica token (sem expiração no seu cenário)
    token_data = AuthService.verify_token(credentials.credentials)
    if token_data is None or not token_data.email:
        raise unauthorized_exc

    # Busca usuário por e-mail normalizado
    user = AuthService.get_user_by_email(db, email=token_data.email)
    if user is None:
        # Token válido, mas usuário não existe mais → 401
        raise unauthorized_exc

    return user


def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """
    Garante que o usuário esteja ativo. Mantém o retorno do objeto User completo.
    """
    if not current_user.is_active:
        # Pode ser 403 (forbidden). Mantive 400 pois era seu comportamento atual.
        # Se preferir semântica mais comum, troque para status_code=403.
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Usuário inativo",
        )
    return current_user
