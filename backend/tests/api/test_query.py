import pytest

from app.main import create_app


class Service:
    async def query(self, question, history):
        if question == "timeout":
            raise TimeoutError
        return {"answer": "有 1 筆資料", "cases": [], "price_reference": None, "citations": [],
                "limitations": [], "sync_metadata": {"status": "ready"}}


@pytest.mark.anyio
async def test_local_frontend_can_preflight_json_query(client_factory):
    async with client_factory(create_app(Service())) as client:
        response = await client.options("/api/query", headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        })
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"


@pytest.mark.anyio
async def test_cors_does_not_allow_unknown_origins(client_factory):
    async with client_factory(create_app(Service())) as client:
        response = await client.options("/api/query", headers={
            "Origin": "https://untrusted.example", "Access-Control-Request-Method": "POST",
        })
    assert "access-control-allow-origin" not in response.headers


@pytest.mark.anyio
async def test_query_endpoint_returns_structured_response(client_factory):
    async with client_factory(create_app(Service())) as client:
        response = await client.post("/api/query", json={"question": "找資訊案件"})
    assert response.status_code == 200
    assert response.json()["sync_metadata"]["status"] == "ready"


@pytest.mark.anyio
async def test_query_endpoint_handles_timeout(client_factory):
    async with client_factory(create_app(Service())) as client:
        response = await client.post("/api/query", json={"question": "timeout"})
    assert response.status_code == 200
    assert response.json()["limitations"] == ["模型回應逾時，請稍後重試。"]


@pytest.mark.anyio
async def test_default_app_reports_configuration_requirement(client_factory):
    async with client_factory(create_app()) as client:
        response = await client.post("/api/query", json={"question": "找案件"})
    assert response.status_code == 200
    assert response.json()["sync_metadata"]["status"] == "configuration_required"
