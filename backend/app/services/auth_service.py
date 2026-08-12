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
SECRET_KEY = os.getenv(
    "SECRET_KEY",
    "sua-chave-secreta-super-segura-aqui-mude-em-producao"
)
ALGORITHM = "HS256"
ISSUER = os.getenv("JWT_ISS", "jip-api")   # opcional
AUDIENCE = os.getenv("JWT_AUD", "jip-clients")  # opcional

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
        """
        Cria token JWT.
        *Sem expiração* por padrão, para seu cenário atual.
        - Adiciona `iat` (emitido em) e `jti` (ID único do token) automaticamente.
        - Mantém o `sub` que você já envia (email).
        - `iss` e `aud` são adicionados de forma informativa (não obrigatórios).
        """
        to_encode = data.copy()

        # Campos úteis para auditoria/possível revogação futura.
        now = datetime.now(timezone.utc)
        to_encode.setdefault("iat", int(now.timestamp()))
        to_encode.setdefault("jti", str(uuid4()))
        to_encode.setdefault("iss", ISSUER)
        to_encode.setdefault("aud", AUDIENCE)

        # Importante: NÃO definir "exp" (expiração) no seu cenário atual.
        # Mantemos a assinatura de função aceita 'expires_delta' apenas por compatibilidade.

        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt

    @staticmethod
    def verify_token(token: str) -> Optional[TokenData]:
        """
        Verifica e decodifica token (sem expiração).
        - Valida assinatura/algoritmo.
        - Extrai `sub` como e-mail (compatível com seu fluxo atual).
        Retorna TokenData(email=...) se ok; senão, None.
        """
        try:
            payload = jwt.decode(
                token,
                SECRET_KEY,
                algorithms=[ALGORITHM],
                options={
                    "verify_signature": True,
                    "verify_aud": False,  # ajuste pra True se quiser checar AUDIENCE
                    "verify_iss": False,  # ajuste pra True se quiser checar ISSUER
                    "verify_exp": False,  # sem expiração
                },
                # audience=AUDIENCE,  # habilite se ativar verify_aud
                # issuer=ISSUER,      # habilite se ativar verify_iss
            )
            email = payload.get("sub")
            if not email:
                return None
            return TokenData(email=email)
        except JWTError as e:
            print(f"❌ Erro ao verificar token: {e}")
            return None
