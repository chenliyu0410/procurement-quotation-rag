from fastapi import FastAPI

from app.api.query import router as query_router


class UnconfiguredQueryService:
    async def query(self, question, history):
        return {"answer": "查詢服務尚未完成模型與索引設定。", "cases": [], "price_reference": None,
                "citations": [], "limitations": ["請先同步資料並設定模型 API。"],
                "sync_metadata": {"status": "configuration_required"}}


def create_app(query_service=None) -> FastAPI:
    app = FastAPI(
        title="Procurement & Quotation Knowledge Assistant",
        version="0.1.0",
    )
    app.state.query_service = query_service or UnconfiguredQueryService()
    app.include_router(query_router)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
