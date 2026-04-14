from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Broadcaster
from app.schemas import BroadcasterOut
from app.auth import get_current_user

router = APIRouter(prefix="/api/broadcasters", tags=["broadcasters"])


@router.get("", response_model=list[BroadcasterOut])
def list_broadcasters(db: Session = Depends(get_db), _=Depends(get_current_user)):
    return db.query(Broadcaster).all()
