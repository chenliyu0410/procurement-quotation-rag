from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.query import router as query_router
from app.api.sources import router as sources_router
from app.db.session import build_session_factory
from app.config import get_settings


class UnconfiguredQueryService:
    async def query(self, question, history):
        return {"answer": "查詢服務尚未完成模型與索引設定。", "cases": [], "price_reference": None,
                "citations": [], "limitations": ["請先同步資料並設定模型 API。"],
                "sync_metadata": {"status": "configuration_required"}}


def create_app(query_service=None) -> FastAPI:
    from app.runtime import build_query_service
    app = FastAPI(
        title="Procurement & Quotation Knowledge Assistant",
        version="0.1.0",
    )
    app.state.query_service = query_service if query_service is not None else (build_query_service(get_settings()) or UnconfiguredQueryService())
    app.state.session_factory = build_session_factory()
    app.add_middleware(CORSMiddleware, allow_origins=get_settings().cors_origins,
                       allow_methods=["POST", "GET"], allow_headers=["Content-Type"])
    app.include_router(query_router)
    app.include_router(sources_router)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
