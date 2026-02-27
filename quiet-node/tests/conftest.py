import pytest
from httpx import ASGITransport, AsyncClient

from server.app.db import init_db
from server.app.main import app


@pytest.fixture(autouse=True)
def _reset_db():
    """Give each test a fresh in-memory database."""
    app.state.db = init_db(":memory:")
    yield
    app.state.db.close()


@pytest.fixture
def client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")
