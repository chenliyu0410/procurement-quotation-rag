from sqlalchemy import Select, select
from sqlalchemy.orm import Session
from collections.abc import Sequence

from app.db.models import ProcurementCase
from app.search.schemas import CaseFilters, CaseResult


class CaseRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def search(self, filters: CaseFilters, limit: int = 50, *, case_ids: Sequence[str] | None = None) -> list[CaseResult]:
        if limit < 1 or limit > 200:
            raise ValueError("limit must be between 1 and 200")
        statement: Select[tuple[ProcurementCase]] = select(ProcurementCase).where(ProcurementCase.is_active.is_(True))
        if case_ids is not None:
            if not case_ids:
                return []
            statement = statement.where(ProcurementCase.id.in_(case_ids))
        amount = ProcurementCase.budget_amount if filters.amount_kind == "budget" else ProcurementCase.award_amount
        date_column = ProcurementCase.expected_tender_date if filters.amount_kind == "budget" else ProcurementCase.announcement_date
        if filters.agency:
            statement = statement.where(ProcurementCase.agency.contains(filters.agency, autoescape=True))
        if filters.category:
            statement = statement.where(ProcurementCase.category_normalized == filters.category)
        if filters.min_amount is not None:
            statement = statement.where(amount >= filters.min_amount)
        if filters.max_amount is not None:
            statement = statement.where(amount <= filters.max_amount)
        if filters.start_date:
            statement = statement.where(date_column >= filters.start_date)
        if filters.end_date:
            statement = statement.where(date_column <= filters.end_date)
        cases = self.session.scalars(statement.order_by(date_column.desc(), ProcurementCase.id).limit(limit)).all()
        return [CaseResult(id=item.id, agency=item.agency, case_name=item.case_name, category=item.category_normalized,
            budget_amount=item.budget_amount, award_amount=item.award_amount, announcement_date=item.announcement_date,
            expected_tender_date=item.expected_tender_date, source_url=item.source_url) for item in cases]
