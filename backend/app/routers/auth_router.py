"""
app/routers/auth_router.py

Rotas de autenticação de usuários.

🚨 Alteração importante:
- O token JWT gerado **não tem mais tempo de expiração**.
- Se quiser que o token expire (sessão temporária), reative a lógica de timedelta em /login.
- Como não expira, aumenta o risco se o token for roubado → em produção, considere refresh tokens.

Dependências:
- Usa AuthService (app/services/auth_service.py) para criar usuário, autenticar e gerar tokens.
- O retorno do AuthService.create_access_token agora não recebe `expires_delta`.

Rotas:
- POST /register     → Cria novo usuário (email + senha).
- POST /login        → Faz login e retorna token permanente + dados do usuário.
- GET  /me           → Retorna usuário autenticado via token.
- GET  /verify-token → Valida token informado no header Authorization.
"""

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
    Autentica usuário e retorna token de acesso **sem expiração**.
    
    - **email**: Email do usuário
    - **password**: Senha do usuário
    
    Retorna token JWT (sem expiração) para usar nas próximas requisições.
    """
    try:
        user = AuthService.authenticate_user(
            db, user_credentials.email, user_credentials.password
        )
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email ou senha incorretos",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Token permanente (sem tempo de expiração)
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
    Verifica se o token ainda é válido (mesmo sem expiração).
    """
    return {"message": "Token válido", "user": current_user}
