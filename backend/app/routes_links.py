from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import ItemTechLink, PolicyItem, TechItem, User, gen_id
from app.schemas import ItemTechLinkCreate, ItemTechLinkOut, TechItemOut, PolicyItemOut
from app.auth import get_current_user, require_role

router = APIRouter(prefix="/api/links", tags=["links"])


# ── 전체 연결 ────────────────────────────────────────────────────

@router.get("", response_model=list[ItemTechLinkOut])
def list_links(db: Session = Depends(get_db), _=Depends(get_current_user)):
    return db.query(ItemTechLink).all()


# ── 정책 항목 → 연결된 기술 항목들 ────────────────────────────────

@router.get("/by-policy-item/{policy_item_id}", response_model=list[TechItemOut])
def tech_by_policy_item(policy_item_id: str, db: Session = Depends(get_db), _=Depends(get_current_user)):
    links = db.query(ItemTechLink).filter(ItemTechLink.policy_item_id == policy_item_id).all()
    tech_ids = [l.tech_item_id for l in links]
    if not tech_ids:
        return []
    return db.query(TechItem).filter(TechItem.id.in_(tech_ids)).all()


# ── 기술 항목 → 연결된 정책 항목들 ────────────────────────────────

@router.get("/by-tech-item/{tech_item_id}", response_model=list[PolicyItemOut])
def policy_by_tech_item(tech_item_id: str, db: Session = Depends(get_db), _=Depends(get_current_user)):
    links = db.query(ItemTechLink).filter(ItemTechLink.tech_item_id == tech_item_id).all()
    item_ids = [l.policy_item_id for l in links]
    if not item_ids:
        return []
    return db.query(PolicyItem).filter(PolicyItem.id.in_(item_ids)).all()


# ── 연결 추가 / 삭제 (admin / dev) ───────────────────────────────

@router.post("", response_model=ItemTechLinkOut, status_code=201)
def create_link(body: ItemTechLinkCreate, db: Session = Depends(get_db), user: User = Depends(require_role("dev"))):
    item = db.query(PolicyItem).filter(PolicyItem.id == body.policy_item_id).first()
    if not item:
        raise HTTPException(404, "Policy item not found")
    tech = db.query(TechItem).filter(TechItem.id == body.tech_item_id).first()
    if not tech:
        raise HTTPException(404, "Tech item not found")

    exists = (
        db.query(ItemTechLink)
        .filter(ItemTechLink.policy_item_id == body.policy_item_id,
                ItemTechLink.tech_item_id == body.tech_item_id)
        .first()
    )
    if exists:
        return exists

    link = ItemTechLink(id=gen_id(), policy_item_id=body.policy_item_id, tech_item_id=body.tech_item_id, note=body.note)
    db.add(link)
    db.commit()
    db.refresh(link)
    return link


@router.delete("/{link_id}")
def delete_link(link_id: str, db: Session = Depends(get_db), user: User = Depends(require_role("dev"))):
    link = db.query(ItemTechLink).filter(ItemTechLink.id == link_id).first()
    if not link:
        raise HTTPException(404, "Link not found")
    db.delete(link)
    db.commit()
    return {"ok": True}