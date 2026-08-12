# app/database/database.py

import os
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

# Para conexão assíncrona com a lib 'databases'
from databases import Database


# -------------------------------
# Carregar variáveis do .env
# -------------------------------
load_dotenv()


# -------------------------------
# Helpers para padronizar URLs
# -------------------------------
def ensure_sslmode(url: str) -> str:
    """
    Garante sslmode=require em URLs PostgreSQL (Neon exige).
    Se já houver sslmode, mantém.
    """
    p = urlparse(url)
    qs = parse_qs(p.query)
    if p.scheme.startswith("postgresql") and "sslmode" not in qs:
        qs["sslmode"] = ["require"]
    new_q = urlencode(qs, doseq=True)
    return urlunparse(p._replace(query=new_q))


def to_sqlalchemy_psycopg(url: str) -> str:
    """
    Garante driver psycopg3 para SQLAlchemy: postgresql+psycopg://
    (Mantém outros esquemas, ex.: sqlite://, se for o caso)
    """
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


def to_databases_asyncpg(url: str) -> str:
    """
    A lib 'databases' usa o driver asyncpg em PostgreSQL: postgresql+asyncpg://
    """
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if url.startswith("postgresql+psycopg://"):
        return url.replace("postgresql+psycopg://", "postgresql+asyncpg://", 1)
    return url


# -------------------------------
# Ler DATABASE_URL do ambiente
# -------------------------------
DATABASE_URL_RAW = os.getenv("DATABASE_URL")
if not DATABASE_URL_RAW:
    raise RuntimeError(
        "DATABASE_URL não encontrada. Coloque sua URL do Neon no .env, ex:\n"
        "DATABASE_URL=postgresql://user:senha@host.neon.tech/dbname"
    )

# Força sslmode=require e drivers corretos
DATABASE_URL_RAW = ensure_sslmode(DATABASE_URL_RAW)

SQLALCHEMY_URL = to_sqlalchemy_psycopg(DATABASE_URL_RAW)
DATABASES_URL  = to_databases_asyncpg(DATABASE_URL_RAW)

# -------------------------------
# SQLAlchemy (sincrono)
# -------------------------------
# Observação: nada de connect_args={"check_same_thread": False} (isso é só para SQLite).
engine = create_engine(
    SQLALCHEMY_URL,
    pool_pre_ping=True,
    future=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    future=True,
)

Base = declarative_base()

# -------------------------------
# 'databases' (assíncrono)
# -------------------------------
database = Database(DATABASES_URL)


# -------------------------------
# Dependency para obter sessão (FastAPI)
# -------------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
