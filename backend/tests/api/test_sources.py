import pytest
from app.main import create_app
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.db.models import Base, ProcurementCase


@pytest.mark.anyio
async def test_sources_reports_database_counts(client_factory):
    app = create_app()
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    app.state.session_factory = sessionmaker(engine)
    with app.state.session_factory() as session:
        for i in range(6):
            session.add(ProcurementCase(id=str(i), source_dataset="fixture", agency="工務局",
                case_name="案件", category_normalized="工程", source_row_hash=str(i), source_url="https://example.org"))
        session.commit()
    async with client_factory(app) as client:
        response = await client.get("/api/sources")
    assert response.status_code == 200
    assert response.json()["sources"][0]["record_count"] == 6
