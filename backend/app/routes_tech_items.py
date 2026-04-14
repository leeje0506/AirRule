from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import TechItem, TechItemHistory, User
from app.schemas import TechItemCreate, TechItemUpdate, TechItemOut, TechItemHistoryOut
from app.auth import get_current_user, require_role
from app.models import gen_id, utcnow

router = APIRouter(prefix="/api/tech-items", tags=["tech-items"])


@router.get("", response_model=list[TechItemOut])
def list_tech_items(db: Session = Depends(get_db), _=Depends(get_current_user)):
    return db.query(TechItem).order_by(TechItem.updated_at.desc()).all()


@router.get("/{item_id}", response_model=TechItemOut)
def get_tech_item(item_id: str, db: Session = Depends(get_db), _=Depends(get_current_user)):
    item = db.query(TechItem).filter(TechItem.id == item_id).first()
    if not item:
        raise HTTPException(404, "Item not found")
    return item


@router.post("", response_model=TechItemOut, status_code=201)
def create_tech_item(body: TechItemCreate, db: Session = Depends(get_db), user: User = Depends(require_role("dev"))):
    item = TechItem(
        id=gen_id(),
        type=body.type,
        name=body.name,
        desc=body.desc,
        params=body.params,
        scope=body.scope,
        tag=body.tag,
        source_code=body.source_code,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.put("/{item_id}", response_model=TechItemOut)
def update_tech_item(item_id: str, body: TechItemUpdate, db: Session = Depends(get_db), user: User = Depends(require_role("dev"))):
    item = db.query(TechItem).filter(TechItem.id == item_id).first()
    if not item:
        raise HTTPException(404, "Item not found")

    changes = []
    for field in ["name", "desc", "params", "scope", "tag", "source_code"]:
        val = getattr(body, field)
        if val is not None:
            setattr(item, field, val)
            changes.append(f"{field} 변경")

    item.updated_at = utcnow()

    history = TechItemHistory(
        id=gen_id(),
        item_id=item_id,
        edited_by=user.id,
        summary=body.edit_summary or "; ".join(changes),
    )
    db.add(history)
    db.commit()
    db.refresh(item)
    return item


@router.get("/{item_id}/history", response_model=list[TechItemHistoryOut])
def get_tech_item_history(item_id: str, db: Session = Depends(get_db), _=Depends(get_current_user)):
    return (
        db.query(TechItemHistory)
        .filter(TechItemHistory.item_id == item_id)
        .order_by(TechItemHistory.edited_at.desc())
        .all()
    )
