from fastapi import APIRouter, HTTPException

from app.database.history_repository import get_recent_history, get_history_by_id, QueryHistoryRecord

router = APIRouter(prefix="/history", tags=["history"])


@router.get("", response_model=list[QueryHistoryRecord])
def list_history(limit: int = 50) -> list[QueryHistoryRecord]:
    return get_recent_history(limit=limit)


@router.get("/{record_id}", response_model=QueryHistoryRecord)
def get_history_item(record_id: int) -> QueryHistoryRecord:
    record = get_history_by_id(record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="History record not found")
    return record