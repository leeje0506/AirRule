from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import (
    PolicyCategory, PolicyItem, PolicyValue, PolicyValueHistory,
    Broadcaster, User, gen_id, utcnow,
)
from app.schemas import (
    PolicyCategoryOut, PolicyCategoryCreate, PolicyCategoryUpdate,
    PolicyItemOut, PolicyItemCreate, PolicyItemUpdate,
    PolicyValueOut, PolicyValueUpsert, PolicyValueHistoryOut,
)
from app.auth import get_current_user, require_role

router = APIRouter(prefix="/api/policies", tags=["policies"])


# ── 전체 매트릭스 조회 (카테고리 → 항목 → 셀값 트리) ──────────────

@router.get("", response_model=list[PolicyCategoryOut])
def get_matrix(db: Session = Depends(get_db), _=Depends(get_current_user)):
    return (
        db.query(PolicyCategory)
        .order_by(PolicyCategory.sort_order)
        .all()
    )


# ── 카테고리 CRUD (자막팀) ───────────────────────────────────────

@router.post("/categories", response_model=PolicyCategoryOut, status_code=201)
def create_category(body: PolicyCategoryCreate, db: Session = Depends(get_db), user: User = Depends(require_role("subtitle"))):
    cat = PolicyCategory(id=gen_id(), name=body.name, sort_order=body.sort_order)
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return cat


@router.put("/categories/{cat_id}", response_model=PolicyCategoryOut)
def update_category(cat_id: str, body: PolicyCategoryUpdate, db: Session = Depends(get_db), user: User = Depends(require_role("subtitle"))):
    cat = db.query(PolicyCategory).filter(PolicyCategory.id == cat_id).first()
    if not cat:
        raise HTTPException(404, "Category not found")
    if body.name is not None:
        cat.name = body.name
    if body.sort_order is not None:
        cat.sort_order = body.sort_order
    db.commit()
    db.refresh(cat)
    return cat


@router.delete("/categories/{cat_id}")
def delete_category(cat_id: str, db: Session = Depends(get_db), user: User = Depends(require_role("subtitle"))):
    cat = db.query(PolicyCategory).filter(PolicyCategory.id == cat_id).first()
    if not cat:
        raise HTTPException(404, "Category not found")
    db.delete(cat)  # items/values cascade
    db.commit()
    return {"ok": True}


# ── 항목 CRUD (자막팀) ───────────────────────────────────────────

@router.post("/items", response_model=PolicyItemOut, status_code=201)
def create_item(body: PolicyItemCreate, db: Session = Depends(get_db), user: User = Depends(require_role("subtitle"))):
    cat = db.query(PolicyCategory).filter(PolicyCategory.id == body.category_id).first()
    if not cat:
        raise HTTPException(404, "Category not found")
    item = PolicyItem(
        id=gen_id(),
        category_id=body.category_id,
        name=body.name,
        description=body.description,
        sort_order=body.sort_order,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.put("/items/{item_id}", response_model=PolicyItemOut)
def update_item(item_id: str, body: PolicyItemUpdate, db: Session = Depends(get_db), user: User = Depends(require_role("subtitle"))):
    item = db.query(PolicyItem).filter(PolicyItem.id == item_id).first()
    if not item:
        raise HTTPException(404, "Item not found")
    if body.name is not None:
        item.name = body.name
    if body.description is not None:
        item.description = body.description
    if body.sort_order is not None:
        item.sort_order = body.sort_order
    db.commit()
    db.refresh(item)
    return item


@router.delete("/items/{item_id}")
def delete_item(item_id: str, db: Session = Depends(get_db), user: User = Depends(require_role("subtitle"))):
    item = db.query(PolicyItem).filter(PolicyItem.id == item_id).first()
    if not item:
        raise HTTPException(404, "Item not found")
    db.delete(item)  # values/links cascade
    db.commit()
    return {"ok": True}


# ── 셀 값 upsert (항목 × 방송사) — 변경 시 이력 자동 기록 ──────────

@router.put("/values", response_model=PolicyValueOut)
def upsert_value(body: PolicyValueUpsert, db: Session = Depends(get_db), user: User = Depends(require_role("subtitle"))):
    item = db.query(PolicyItem).filter(PolicyItem.id == body.item_id).first()
    if not item:
        raise HTTPException(404, "Item not found")
    bc = db.query(Broadcaster).filter(Broadcaster.id == body.broadcaster_id).first()
    if not bc:
        raise HTTPException(404, "Broadcaster not found")

    pv = (
        db.query(PolicyValue)
        .filter(PolicyValue.item_id == body.item_id, PolicyValue.broadcaster_id == body.broadcaster_id)
        .first()
    )

    if pv:
        if pv.summary != body.summary or pv.detail != body.detail:
            db.add(PolicyValueHistory(
                id=gen_id(), value_id=pv.id, edited_by=user.id,
                old_summary=pv.summary, new_summary=body.summary,
                old_detail=pv.detail, new_detail=body.detail, note=body.note,
            ))
            pv.summary = body.summary
            pv.detail = body.detail
            pv.updated_at = utcnow()
    else:
        pv = PolicyValue(
            id=gen_id(), item_id=body.item_id, broadcaster_id=body.broadcaster_id,
            summary=body.summary, detail=body.detail,
        )
        db.add(pv)
        db.flush()
        db.add(PolicyValueHistory(
            id=gen_id(), value_id=pv.id, edited_by=user.id,
            old_summary="", new_summary=body.summary,
            old_detail="", new_detail=body.detail, note=body.note or "신규 생성",
        ))

    db.commit()
    db.refresh(pv)
    return pv


# ── 셀 단위 변경 이력 ─────────────────────────────────────────────

@router.get("/values/{value_id}/history", response_model=list[PolicyValueHistoryOut])
def get_value_history(value_id: str, db: Session = Depends(get_db), _=Depends(get_current_user)):
    return (
        db.query(PolicyValueHistory)
        .filter(PolicyValueHistory.value_id == value_id)
        .order_by(PolicyValueHistory.edited_at.desc())
        .all()
    )


# ── 전체 정책 변경 이력 (항목·방송사명 포함) ──────────────────────

@router.get("/history")
def all_policy_history(db: Session = Depends(get_db), _=Depends(get_current_user)):
    rows = (
        db.query(PolicyValueHistory, PolicyValue, PolicyItem, Broadcaster)
        .join(PolicyValue, PolicyValueHistory.value_id == PolicyValue.id)
        .join(PolicyItem, PolicyValue.item_id == PolicyItem.id)
        .join(Broadcaster, PolicyValue.broadcaster_id == Broadcaster.id)
        .order_by(PolicyValueHistory.edited_at.desc())
        .all()
    )
    result = []
    for h, v, item, bc in rows:
        result.append({
            "id": h.id,
            "kind": "policy",
            "item_name": item.name,
            "broadcaster": bc.name,
            "edited_by": h.edited_by,
            "edited_at": h.edited_at.isoformat() if h.edited_at else None,
            "old_summary": h.old_summary,
            "new_summary": h.new_summary,
            "old_detail": h.old_detail,
            "new_detail": h.new_detail,
            "note": h.note,
        })
    return result