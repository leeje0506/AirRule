from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Policy, PolicyHistory, User
from app.schemas import PolicyCreate, PolicyUpdate, PolicyOut, PolicyHistoryOut
from app.auth import get_current_user, require_role
from app.models import gen_id, utcnow

router = APIRouter(prefix="/api/policies", tags=["policies"])


@router.get("", response_model=list[PolicyOut])
def list_policies(db: Session = Depends(get_db), _=Depends(get_current_user)):
    return db.query(Policy).order_by(Policy.updated_at.desc()).all()


@router.get("/{policy_id}", response_model=PolicyOut)
def get_policy(policy_id: str, db: Session = Depends(get_db), _=Depends(get_current_user)):
    pol = db.query(Policy).filter(Policy.id == policy_id).first()
    if not pol:
        raise HTTPException(404, "Policy not found")
    return pol


@router.post("", response_model=PolicyOut, status_code=201)
def create_policy(body: PolicyCreate, db: Session = Depends(get_db), user: User = Depends(require_role("subtitle"))):
    pol = Policy(
        id=gen_id(),
        broadcaster_id=body.broadcaster_id,
        title=body.title,
        version=body.version,
        status=body.status,
        rules=body.rules,
        created_by=user.id,
    )
    db.add(pol)
    db.commit()
    db.refresh(pol)
    return pol


@router.put("/{policy_id}", response_model=PolicyOut)
def update_policy(policy_id: str, body: PolicyUpdate, db: Session = Depends(get_db), user: User = Depends(require_role("subtitle"))):
    pol = db.query(Policy).filter(Policy.id == policy_id).first()
    if not pol:
        raise HTTPException(404, "Policy not found")

    changes = []
    for field in ["title", "version", "status", "rules"]:
        val = getattr(body, field)
        if val is not None:
            setattr(pol, field, val)
            changes.append(f"{field} 변경")

    pol.updated_at = utcnow()

    history = PolicyHistory(
        id=gen_id(),
        policy_id=policy_id,
        edited_by=user.id,
        summary=body.edit_summary or "; ".join(changes),
    )
    db.add(history)
    db.commit()
    db.refresh(pol)
    return pol


@router.delete("/{policy_id}")
def delete_policy(policy_id: str, db: Session = Depends(get_db), user: User = Depends(require_role("subtitle"))):
    pol = db.query(Policy).filter(Policy.id == policy_id).first()
    if not pol:
        raise HTTPException(404, "Policy not found")
    db.delete(pol)
    db.commit()
    return {"ok": True}


@router.get("/{policy_id}/history", response_model=list[PolicyHistoryOut])
def get_policy_history(policy_id: str, db: Session = Depends(get_db), _=Depends(get_current_user)):
    return (
        db.query(PolicyHistory)
        .filter(PolicyHistory.policy_id == policy_id)
        .order_by(PolicyHistory.edited_at.desc())
        .all()
    )
