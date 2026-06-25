from pydantic import BaseModel
from typing import Optional
from datetime import datetime


# ── Auth ─────────────────────────────────────────────────────────
#   (기존 그대로 — 로그인 구조 유지)

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
#   (기존 그대로)

class BroadcasterOut(BaseModel):
    id: str
    code: str
    name: str
    color: str

    class Config:
        from_attributes = True


# ── Policy Matrix (NEW) ──────────────────────────────────────────

class PolicyValueOut(BaseModel):
    id: str
    item_id: str
    broadcaster_id: str
    summary: str = ""
    detail: str = ""
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class PolicyItemOut(BaseModel):
    id: str
    category_id: str
    name: str
    description: str = ""
    sort_order: int = 0
    values: list[PolicyValueOut] = []

    class Config:
        from_attributes = True

class PolicyCategoryOut(BaseModel):
    id: str
    name: str
    sort_order: int = 0
    items: list[PolicyItemOut] = []

    class Config:
        from_attributes = True


# 카테고리 CRUD
class PolicyCategoryCreate(BaseModel):
    name: str
    sort_order: int = 0

class PolicyCategoryUpdate(BaseModel):
    name: Optional[str] = None
    sort_order: Optional[int] = None


# 항목 CRUD
class PolicyItemCreate(BaseModel):
    category_id: str
    name: str
    description: str = ""
    sort_order: int = 0

class PolicyItemUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    sort_order: Optional[int] = None


# 셀 값 upsert (항목 × 방송사) — 변경 시 이력 자동 기록
class PolicyValueUpsert(BaseModel):
    item_id: str
    broadcaster_id: str
    summary: str = ""
    detail: str = ""
    note: str = ""  # 변경 사유/메모 (이력에 기록)

class PolicyValueHistoryOut(BaseModel):
    id: str
    value_id: str
    edited_by: Optional[str] = None
    edited_at: Optional[datetime] = None
    old_summary: str = ""
    new_summary: str = ""
    old_detail: str = ""
    new_detail: str = ""
    note: str = ""

    class Config:
        from_attributes = True


# ── Tech Item ────────────────────────────────────────────────────
#   (기존 그대로 — 개발팀 영역)

class TechItemCreate(BaseModel):
    type: str
    name: str
    function_name: str = ""
    func_type: str = "content_only"
    stage: str = "stage1"
    desc: str = ""
    params: dict = {}
    scope: str = "common"
    tag: str = "planned"
    source_code: str = ""

class TechItemUpdate(BaseModel):
    name: Optional[str] = None
    function_name: Optional[str] = None
    func_type: Optional[str] = None
    stage: Optional[str] = None
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
    function_name: str = ""
    func_type: str = "content_only"
    stage: str = "stage1"
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


# ── Item ↔ Tech link (NEW) ───────────────────────────────────────
#   3번 페이지: 정책 항목 ↔ 기술 항목 연결

class ItemTechLinkCreate(BaseModel):
    policy_item_id: str
    tech_item_id: str
    note: str = ""

class ItemTechLinkOut(BaseModel):
    id: str
    policy_item_id: str
    tech_item_id: str
    note: str = ""

    class Config:
        from_attributes = True


# ── Mapping ──────────────────────────────────────────────────────
#   (기존 그대로 — 테스트 파이프라인용)

class MappingUpdate(BaseModel):
    item_ids: list[str]

class MappingOut(BaseModel):
    broadcaster_id: str
    items: list[TechItemOut]