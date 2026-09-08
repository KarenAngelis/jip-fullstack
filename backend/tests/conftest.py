"""Real auth/settings routers and real SQL, isolated from external providers."""
import os

# Set before application imports; never read a developer's database or signing key.
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["SECRET_KEY"] = "jip-tests-only-not-a-production-key-000000000"
os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"] = "30"
os.environ["JWT_ISS"] = "jip-api"
os.environ["JWT_AUD"] = "jip-clients"

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.database.database import Base, get_db
from app.models.user_model import User
from app.models.account_settings_model import AccountSettings
from app.routers.auth_router import router as auth_router
from app.routers.settings_router import router as settings_router


@pytest.fixture
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    Base.metadata.create_all(engine, tables=[User.__table__, AccountSettings.__table__])
    with sessionmaker(bind=engine)() as session:
        yield session
    engine.dispose()


@pytest.fixture
def client(db):
    app = FastAPI()
    app.include_router(auth_router, prefix="/api/auth")
    app.include_router(settings_router)

    def test_db():
        yield db

    app.dependency_overrides[get_db] = test_db
    with TestClient(app) as client:
        yield client


@pytest.fixture
def accounts(client):
    accounts = []
    for name in ("alice", "bob"):
        credentials = {"email": f"{name}@example.com", "password": "Test-password-42!"}
        registered = client.post("/api/auth/register", json={**credentials, "nome": name})
        assert registered.status_code == 200
        login = client.post("/api/auth/login", json=credentials)
        assert login.status_code == 200
        accounts.append({**registered.json(), "credentials": credentials,
                         "token": login.json()["access_token"]})
    return accounts


@pytest.fixture
def auth_headers():
    return lambda account: {"Authorization": f"Bearer {account['token']}"}
