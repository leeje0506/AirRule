from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import union_all, literal_column, select
from app.database import get_db
from app.models import Mapping, TechItem
from app.schemas import MappingUpdate, MappingOut, TechItemOut
from app.readonly import guard_write
from app.auth import get_current_user
from app.models import gen_id

router = APIRouter(tags=["mappings"])


def _items_in_order(db: Session, item_ids):
    """id 목록의 순서를 그대로 유지한 TechItem 목록. (IN 조회는 순서를 보장하지 않는다)"""
    if not item_ids:
        return []
    rows = {it.id: it for it in db.query(TechItem).filter(TechItem.id.in_(item_ids)).all()}
    return [rows[i] for i in item_ids if i in rows]


# ── Mappings ─────────────────────────────────────────────────────

@router.get("/api/mappings/{broadcaster_id}", response_model=MappingOut)
def get_mapping(broadcaster_id: str, db: Session = Depends(get_db), _=Depends(get_current_user)):
    rows = (
        db.query(Mapping)
        .filter(Mapping.broadcaster_id == broadcaster_id)
        .order_by(Mapping.sort_order)
        .all()
    )
    item_ids = [r.item_id for r in rows]
    return MappingOut(broadcaster_id=broadcaster_id, items=_items_in_order(db, item_ids))


@router.put("/api/mappings/{broadcaster_id}", response_model=MappingOut)
def update_mapping(broadcaster_id: str, body: MappingUpdate, db: Session = Depends(get_db), _=Depends(get_current_user)):
    # Clear existing
    guard_write()
    db.query(Mapping).filter(Mapping.broadcaster_id == broadcaster_id).delete()
    # Insert new — 보내온 순서를 그대로 실행 순서로 저장
    for order, item_id in enumerate(body.item_ids):
        db.add(Mapping(id=gen_id(), broadcaster_id=broadcaster_id, item_id=item_id, sort_order=order))
    db.commit()

    return MappingOut(broadcaster_id=broadcaster_id, items=_items_in_order(db, body.item_ids))
