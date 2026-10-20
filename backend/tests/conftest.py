import pytest
from httpx import ASGITransport, AsyncClient


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
async def client() -> AsyncClient:
    from app.main import create_app

    async with AsyncClient(
        transport=ASGITransport(app=create_app()),
        base_url="http://test",
    ) as test_client:
        yield test_client


@pytest.fixture
def client_factory():
    def factory(app):
        return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
    return factory
