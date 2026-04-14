from pydantic import BaseModel
from typing import Optional
from datetime import datetime


# ── Auth ─────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    token: str
    username: str
    role: str
    name: str

class UserOut(BaseModel):
    username: str
    role: str
    name: str


# ── Broadcaster ──────────────────────────────────────────────────

class BroadcasterOut(BaseModel):
    id: str
    code: str
    name: str
    color: str

    class Config:
        from_attributes = True


# ── Policy ───────────────────────────────────────────────────────

class PolicyCreate(BaseModel):
    broadcaster_id: str
    title: str
    version: str = "v1.0"
    status: str = "draft"
    rules: dict = {}

class PolicyUpdate(BaseModel):
    title: Optional[str] = None
    version: Optional[str] = None
    status: Optional[str] = None
    rules: Optional[dict] = None
    edit_summary: str = ""

class PolicyOut(BaseModel):
    id: str
    broadcaster_id: str
    title: str
    version: str
    status: str
    rules: dict
    created_by: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class PolicyHistoryOut(BaseModel):
    id: str
    policy_id: str
    edited_by: Optional[str] = None
    edited_at: Optional[datetime] = None
    summary: str

    class Config:
        from_attributes = True


# ── Tech Item ────────────────────────────────────────────────────

class TechItemCreate(BaseModel):
    type: str  # processing | validation
    name: str
    desc: str = ""
    params: dict = {}
    scope: str = "common"
    tag: str = "planned"
    source_code: str = ""

class TechItemUpdate(BaseModel):
    name: Optional[str] = None
    desc: Optional[str] = None
    params: Optional[dict] = None
    scope: Optional[str] = None
    tag: Optional[str] = None
    source_code: Optional[str] = None
    edit_summary: str = ""

class TechItemOut(BaseModel):
    id: str
    type: str
    name: str
    desc: str
    params: dict
    scope: str
    tag: str
    source_code: str = ""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class TechItemHistoryOut(BaseModel):
    id: str
    item_id: str
    edited_by: Optional[str] = None
    edited_at: Optional[datetime] = None
    summary: str

    class Config:
        from_attributes = True


# ── Mapping ──────────────────────────────────────────────────────

class MappingUpdate(BaseModel):
    item_ids: list[str]

class MappingOut(BaseModel):
    broadcaster_id: str
    items: list[TechItemOut]
