from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError

from app.db.models import DataSource, DocumentRecord, ProcurementCase, SyncRun


router = APIRouter(prefix="/api")


@router.get("/sources")
def sources(request: Request):
    try:
        with request.app.state.session_factory() as session:
            result = []
            for source_id, count in session.execute(select(ProcurementCase.source_dataset, func.count())
                    .where(ProcurementCase.is_active.is_(True)).group_by(ProcurementCase.source_dataset)):
                source = session.get(DataSource, source_id)
                latest = session.scalar(select(SyncRun).where(SyncRun.source_id == source_id)
                                        .order_by(SyncRun.started_at.desc()).limit(1))
                result.append({"id": source_id, "name": source.name if source else source_id,
                    "source_url": source.dataset_url if source else None, "record_count": count,
                    "period": latest.source_period if latest else "未提供",
                    "last_synced_at": latest.completed_at.isoformat() if latest and latest.completed_at else None,
                    "status": latest.status if latest else "imported"})
            for doc in session.scalars(select(DocumentRecord)):
                result.append({"id": doc.id, "name": doc.filename, "source_url": doc.source,
                    "record_count": doc.chunk_count, "period": "文件版本 " + doc.version_hash[:12],
                    "last_synced_at": doc.indexed_at.isoformat(), "status": "indexed"})
        return {"sources": result}
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail="資料庫暫時無法讀取，請確認服務與 migration。") from exc
