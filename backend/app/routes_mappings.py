from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import union_all, literal_column, select
from app.database import get_db
from app.models import Mapping, TechItem, PolicyHistory, TechItemHistory
from app.schemas import MappingUpdate, MappingOut, TechItemOut
from app.auth import get_current_user
from app.models import gen_id

router = APIRouter(tags=["mappings"])


# ── Mappings ─────────────────────────────────────────────────────

@router.get("/api/mappings/{broadcaster_id}", response_model=MappingOut)
def get_mapping(broadcaster_id: str, db: Session = Depends(get_db), _=Depends(get_current_user)):
    rows = db.query(Mapping).filter(Mapping.broadcaster_id == broadcaster_id).all()
    item_ids = [r.item_id for r in rows]
    items = db.query(TechItem).filter(TechItem.id.in_(item_ids)).all() if item_ids else []
    return MappingOut(broadcaster_id=broadcaster_id, items=items)


@router.put("/api/mappings/{broadcaster_id}", response_model=MappingOut)
def update_mapping(broadcaster_id: str, body: MappingUpdate, db: Session = Depends(get_db), _=Depends(get_current_user)):
    # Clear existing
    db.query(Mapping).filter(Mapping.broadcaster_id == broadcaster_id).delete()
    # Insert new
    for item_id in body.item_ids:
        db.add(Mapping(id=gen_id(), broadcaster_id=broadcaster_id, item_id=item_id))
    db.commit()

    items = db.query(TechItem).filter(TechItem.id.in_(body.item_ids)).all() if body.item_ids else []
    return MappingOut(broadcaster_id=broadcaster_id, items=items)


# ── Global History ───────────────────────────────────────────────

@router.get("/api/history")
def all_history(db: Session = Depends(get_db), _=Depends(get_current_user)):
    policy_h = (
        db.query(PolicyHistory)
        .order_by(PolicyHistory.edited_at.desc())
        .all()
    )
    tech_h = (
        db.query(TechItemHistory)
        .order_by(TechItemHistory.edited_at.desc())
        .all()
    )

    result = []
    for h in policy_h:
        result.append({
            "id": h.id,
            "kind": "policy",
            "ref_id": h.policy_id,
            "edited_by": h.edited_by,
            "edited_at": h.edited_at.isoformat() if h.edited_at else None,
            "summary": h.summary,
        })
    for h in tech_h:
        result.append({
            "id": h.id,
            "kind": "tech",
            "ref_id": h.item_id,
            "edited_by": h.edited_by,
            "edited_at": h.edited_at.isoformat() if h.edited_at else None,
            "summary": h.summary,
        })

    result.sort(key=lambda x: x["edited_at"] or "", reverse=True)
    return result
