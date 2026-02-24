"""
Pytest configuration and fixtures.
"""
import os
import sys
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

# Add app to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import Base, get_db
from app.main import app
from app.models.account import Account
from app.models.role import Role
from app.models.user import User
from app.core.auth import hash_password, create_access_token

# Test database URL - use SQLite for unit tests, Postgres for integration
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql://centro:centro_pass@localhost:5432/centro_control_test"
)

# Create test engine
engine = create_engine(TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session")
def db_engine():
    """Create database engine for tests."""
    # Create all tables
    Base.metadata.create_all(bind=engine)
    yield engine
    # Drop all tables after tests
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db_session(db_engine) -> Generator[Session, None, None]:
    """Create a fresh database session for each test."""
    connection = db_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def client(db_session) -> Generator[TestClient, None, None]:
    """Create test client with overridden DB dependency."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def test_account(db_session) -> Account:
    """Create a test account."""
    account = Account(
        nombre="Test Account",
        api_key="test-api-key-123",
        activo=True,
    )
    db_session.add(account)
    db_session.commit()
    db_session.refresh(account)
    return account


@pytest.fixture(scope="function")
def test_role(db_session, test_account) -> Role:
    """Create a test role with full permissions."""
    role = Role(
        cuenta_id=test_account.id,
        nombre="Admin",
        permisos=["*"],  # All permissions
        activo=True,
    )
    db_session.add(role)
    db_session.commit()
    db_session.refresh(role)
    return role


@pytest.fixture(scope="function")
def test_user(db_session, test_account, test_role) -> User:
    """Create a test user."""
    user = User(
        cuenta_id=test_account.id,
        role_id=test_role.id,
        email="test@example.com",
        hashed_password=hash_password("testpassword123"),
        nombre="Test User",
        activo=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture(scope="function")
def auth_headers(test_user, test_account, test_role) -> dict:
    """Generate authentication headers for test user."""
    token = create_access_token(
        user_id=test_user.id,
        cuenta_id=test_account.id,
        role_id=test_role.id,
        permisos=test_role.permisos,
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="function")
def admin_headers() -> dict:
    """Generate admin API key headers."""
    # Use test admin key from environment or default
    admin_key = os.getenv("ADMIN_API_KEY", "test-admin-key")
    return {"Authorization": f"Bearer {admin_key}"}
