from datetime import date
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.models import Base, ProcurementCase
from app.search.case_repository import CaseRepository
from app.search.schemas import CaseFilters


def add_case(session, case_id, budget, award, announced):
    session.add(ProcurementCase(id=case_id, source_dataset="demo", agency="臺北市政府工務局", case_name="道路工程",
        category_raw="工程", category_normalized="工程", budget_amount=Decimal(budget), award_amount=Decimal(award),
        announcement_date=announced, expected_tender_date=announced, source_period="2024", source_row_hash=case_id,
        source_url="https://example.test", is_active=True))


def test_repository_selects_requested_amount_and_inclusive_dates():
    engine = create_engine("sqlite+pysqlite:///:memory:"); Base.metadata.create_all(engine)
    with Session(engine) as session:
        add_case(session, "a", "500", "90", date(2024, 1, 1)); add_case(session, "b", "100", "500", date(2024, 1, 2)); session.commit()
        budget = CaseRepository(session).search(CaseFilters(min_amount=Decimal("400"), amount_kind="budget", start_date=date(2024, 1, 1), end_date=date(2024, 1, 1)))
        award = CaseRepository(session).search(CaseFilters(min_amount=Decimal("400"), amount_kind="award"))
        assert [item.id for item in budget] == ["a"]
        assert [item.id for item in award] == ["b"]


def test_repository_treats_user_text_as_a_bound_value():
    engine = create_engine("sqlite+pysqlite:///:memory:"); Base.metadata.create_all(engine)
    with Session(engine) as session:
        add_case(session, "a", "500", "90", date(2024, 1, 1)); session.commit()
        assert CaseRepository(session).search(CaseFilters(agency="%' OR 1=1 --")) == []
