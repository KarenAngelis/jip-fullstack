# app/services/auth_service.py

from __future__ import annotations

import os
from datetime import datetime, timezone, timedelta
from typing import Optional
from uuid import uuid4

from fastapi import HTTPException, status
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..models.user_model import User
from ..schemas.auth_schema import UserCreate, TokenData

# -------------------------
# Configurações
# -------------------------
SECRET_KEY = os.getenv("SECRET_KEY", "")
if len(SECRET_KEY) < 32:
    raise RuntimeError("SECRET_KEY must contain at least 32 characters")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
if ACCESS_TOKEN_EXPIRE_MINUTES <= 0:
    raise RuntimeError("ACCESS_TOKEN_EXPIRE_MINUTES must be positive")
ALGORITHM = "HS256"
ISSUER = os.getenv("JWT_ISS", "jip-api")
AUDIENCE = os.getenv("JWT_AUD", "jip-clients")

# Hash de senha (bcrypt ~60 chars). Ajuste o rounds se quiser mais custo.
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:
    """Serviço de autenticação e utilidades relacionadas a usuários."""

    # ---------- Password ----------

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verifica se a senha em texto bate com o hash armazenado."""
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def get_password_hash(password: str) -> str:
        """Gera hash seguro para senha do usuário."""
        return pwd_context.hash(password)

    # ---------- Users ----------

    @staticmethod
    def _normalize_email(email: str) -> str:
        """Normaliza e-mail (trim + lowercase)."""
        return (email or "").strip().lower()

    @staticmethod
    def get_user_by_email(db: Session, email: str) -> Optional[User]:
        """Busca usuário pelo e-mail normalizado."""
        norm = AuthService._normalize_email(email)
        return db.query(User).filter(User.email == norm).first()

    @staticmethod
    def create_user(db: Session, user: UserCreate) -> User:
        """
        Cria novo usuário.
        - Normaliza e-mail
        - Gera hash da senha
        - Evita duplicidade
        """
        norm_email = AuthService._normalize_email(user.email)

        try:
            # Checar existência explícita (além da UNIQUE do DB)
            if AuthService.get_user_by_email(db, norm_email):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email já cadastrado"
                )

            db_user = User(
                email=norm_email,
                hashed_password=AuthService.get_password_hash(user.password),
                nome=user.nome,
                is_active=True,
                is_verified=False,
            )

            db.add(db_user)
            db.commit()
            db.refresh(db_user)

            print(f"✅ Usuário criado: {norm_email}")
            return db_user

        except HTTPException:
            # Não dar rollback aqui, porque nada foi adicionado ainda.
            raise
        except IntegrityError:
            db.rollback()
            # Protege contra condição de corrida de e-mail duplicado
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email já cadastrado"
            )
        except Exception as e:
            db.rollback()
            print(f"❌ Erro ao criar usuário: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erro interno ao criar usuário"
            )

    @staticmethod
    def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
        """
        Autentica usuário por e-mail/senha.
        Retorna User se sucesso; caso contrário, None.
        """
        user = AuthService.get_user_by_email(db, email)
        if not user:
            return None
        if not AuthService.verify_password(password, user.hashed_password):
            return None

        # Atualizar último login (melhor esforço)
        try:
            user.last_login = datetime.now(timezone.utc)
            db.commit()
        except Exception:
            db.rollback()  # evitar transação pendurada
            # Falhar silenciosamente aqui para não quebrar o login

        return user

    # ---------- Tokens ----------

    @staticmethod
    def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """Create a signed, expiring access token for the configured issuer/audience."""
        to_encode = data.copy()
        now = datetime.now(timezone.utc)
        lifetime = expires_delta if expires_delta is not None else timedelta(
            minutes=ACCESS_TOKEN_EXPIRE_MINUTES
        )
        to_encode.update({
            "iat": int(now.timestamp()),
            "exp": int((now + lifetime).timestamp()),
            "jti": str(uuid4()),
            "iss": ISSUER,
            "aud": AUDIENCE,
        })

        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt

    @staticmethod
    def verify_token(token: str) -> Optional[TokenData]:
        """Validate signature, expiry, issuer and audience; reject legacy permanent tokens."""
        try:
            payload = jwt.decode(
                token,
                SECRET_KEY,
                algorithms=[ALGORITHM],
                audience=AUDIENCE,
                issuer=ISSUER,
                options={"require_exp": True, "require_sub": True,
                         "require_iss": True, "require_aud": True},
            )
            email = payload.get("sub")
            if not email:
                return None
            return TokenData(email=email)
        except JWTError as e:
            print(f"❌ Erro ao verificar token: {e}")
            return None
