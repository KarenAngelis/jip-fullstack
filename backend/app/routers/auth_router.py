"""User registration, login and expiring Bearer-token validation."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database.database import get_db
from ..schemas.auth_schema import UserCreate, UserLogin, UserResponse, Token
from ..services.auth_service import AuthService
from ..dependencies.auth import get_current_active_user

router = APIRouter()

@router.post(
    "/register",
    response_model=UserResponse,
    summary="Cadastrar novo usuário"
)
async def register(user: UserCreate, db: Session = Depends(get_db)):
    """
    Cadastra um novo usuário no sistema.
    
    - **email**: Email único do usuário
    - **password**: Senha (será criptografada)
    - **nome**: Nome opcional do usuário
    """
    try:
        db_user = AuthService.create_user(db, user)
        return db_user
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Erro no registro: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor"
        )

@router.post(
    "/login",
    response_model=Token,
    summary="Login do usuário"
)
async def login(user_credentials: UserLogin, db: Session = Depends(get_db)):
    """
    Autentica usuário e retorna token de acesso com expiração.
    
    - **email**: Email do usuário
    - **password**: Senha do usuário
    
    Retorna token JWT com expiração para usar nas próximas requisições.
    """
    try:
        user = AuthService.authenticate_user(
            db, user_credentials.email, user_credentials.password
        )
        
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email ou senha incorretos",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Token com expiração configurável.
        access_token = AuthService.create_access_token(
            data={"sub": user.email}
        )
        
        print(f"✅ Login realizado: {user.email}")
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": user
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Erro no login: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor"
        )

@router.get(
    "/me",
    response_model=UserResponse,
    summary="Obter dados do usuário atual"
)
async def get_me(current_user: UserResponse = Depends(get_current_active_user)):
    """
    Retorna os dados do usuário autenticado.
    
    Requer token de autenticação no header: Authorization: Bearer {token}
    """
    return current_user

@router.get(
    "/verify-token",
    summary="Verificar se token é válido"
)
async def verify_token(current_user: UserResponse = Depends(get_current_active_user)):
    """
    Verifica se o token ainda é válido.
    """
    return {"message": "Token válido", "user": UserResponse.model_validate(current_user)}
