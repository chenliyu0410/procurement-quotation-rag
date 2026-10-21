import pytest
from httpx import ASGITransport, AsyncClient


@pytest.fixture(autouse=True)
def isolate_model_configuration(monkeypatch):
    # A developer's populated .env must not turn unit tests into paid API requests.
    from app.config import get_settings
    for name in ("LLM_API_KEY", "LLM_MODEL", "EMBEDDING_MODEL", "LLM_REASONING_EFFORT"):
        monkeypatch.setenv(name, "")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


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
