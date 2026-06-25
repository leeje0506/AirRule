import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Text, DateTime, ForeignKey, JSON, Integer, Enum as SAEnum
)
from sqlalchemy.orm import relationship
from app.database import Base


def gen_id():
    return uuid.uuid4().hex[:12]


def utcnow():
    return datetime.now(timezone.utc)


# ── Users ────────────────────────────────────────────────────────
#   (기존 그대로 — 로그인 구조 유지)

class User(Base):
    __tablename__ = "users"

    id = Column(String(12), primary_key=True, default=gen_id)
    username = Column(String(50), unique=True, nullable=False, index=True)
    hashed_password = Column(String(128), nullable=False)
    name = Column(String(100), nullable=False)
    role = Column(String(20), nullable=False)  # admin | dev | subtitle
    created_at = Column(DateTime, default=utcnow)


# ── Broadcasters ─────────────────────────────────────────────────
#   (기존 그대로 — 단, 삭제된 Policy 를 가리키던 policies 관계만 제거)

class Broadcaster(Base):
    __tablename__ = "broadcasters"

    id = Column(String(12), primary_key=True, default=gen_id)
    code = Column(String(30), unique=True, nullable=False)  # e.g. jtbc, tving
    name = Column(String(100), nullable=False)
    color = Column(String(10), default="#6366f1")  # hex color


# ── Policy Matrix (NEW) ──────────────────────────────────────────
#   엑셀 시트 구조를 정규화:
#     PolicyCategory (싱크/텍스트/배리어프리/수급납품)
#       └ PolicyItem (오버랩, 글자 수 …)
#            └ PolicyValue (항목 × 방송사 = 셀 하나)
#   셀은 summary(표용 짧은 값)와 detail(방송사별 탭 전문) 두 겹을 가진다.

class PolicyCategory(Base):
    __tablename__ = "policy_categories"

    id = Column(String(12), primary_key=True, default=gen_id)
    name = Column(String(100), nullable=False)  # 싱크, 텍스트, 배리어 프리, 수급/납품
    sort_order = Column(Integer, default=0)

    items = relationship(
        "PolicyItem",
        back_populates="category",
        cascade="all, delete-orphan",
        order_by="PolicyItem.sort_order",
    )


class PolicyItem(Base):
    __tablename__ = "policy_items"

    id = Column(String(12), primary_key=True, default=gen_id)
    category_id = Column(String(12), ForeignKey("policy_categories.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(200), nullable=False)   # 오버랩, 글자 수, 줄 수 …
    description = Column(Text, default="")        # 공통 설명 (시트의 '설명' 열)
    sort_order = Column(Integer, default=0)

    category = relationship("PolicyCategory", back_populates="items")
    values = relationship(
        "PolicyValue",
        back_populates="item",
        cascade="all, delete-orphan",
    )
    tech_links = relationship(
        "ItemTechLink",
        back_populates="policy_item",
        cascade="all, delete-orphan",
    )


class PolicyValue(Base):
    __tablename__ = "policy_values"

    id = Column(String(12), primary_key=True, default=gen_id)
    item_id = Column(String(12), ForeignKey("policy_items.id", ondelete="CASCADE"), nullable=False)
    broadcaster_id = Column(String(12), ForeignKey("broadcasters.id", ondelete="CASCADE"), nullable=False)
    summary = Column(String(100), default="")  # 전체 탭: O / X / △ / 18글자
    detail = Column(Text, default="")          # 방송사별 탭: 풀어쓴 전문
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    item = relationship("PolicyItem", back_populates="values")
    history = relationship(
        "PolicyValueHistory",
        back_populates="value",
        cascade="all, delete-orphan",
        order_by="PolicyValueHistory.edited_at.desc()",
    )


class PolicyValueHistory(Base):
    __tablename__ = "policy_value_history"
    #   셀 단위 변경 이력 — "누가 언제 무엇을 어떻게 바꿨나" (전/후 값 보존)

    id = Column(String(12), primary_key=True, default=gen_id)
    value_id = Column(String(12), ForeignKey("policy_values.id", ondelete="CASCADE"), nullable=False)
    edited_by = Column(String(12), ForeignKey("users.id"), nullable=True)
    edited_at = Column(DateTime, default=utcnow)
    old_summary = Column(String(100), default="")
    new_summary = Column(String(100), default="")
    old_detail = Column(Text, default="")
    new_detail = Column(Text, default="")
    note = Column(Text, default="")  # 변경 사유/메모

    value = relationship("PolicyValue", back_populates="history")


# ── Tech Items (Processing / Validation) ─────────────────────────
#   (기존 그대로 — 개발팀 영역, 2번 페이지)

class TechItem(Base):
    __tablename__ = "tech_items"

    id = Column(String(12), primary_key=True, default=gen_id)
    type = Column(String(20), nullable=False)  # processing | validation
    name = Column(String(200), nullable=False)  # 표시 이름
    function_name = Column(String(200), nullable=False, default="")  # 실제 함수명
    func_type = Column(String(30), default="content_only")  # content_only | content_with_params | timing | multi_subtitle | pair_validation | multi_validation | content_with_validation_params
    stage = Column(String(10), default="stage1")  # stage1 | stage2
    desc = Column(Text, default="")
    params = Column(JSON, default=dict)
    scope = Column(String(20), default="common")  # common | specific
    tag = Column(String(20), default="planned")  # in_progress | applied | planned
    source_code = Column(Text, default="")
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    history = relationship("TechItemHistory", back_populates="tech_item", order_by="TechItemHistory.edited_at.desc()")


class TechItemHistory(Base):
    __tablename__ = "tech_item_history"

    id = Column(String(12), primary_key=True, default=gen_id)
    item_id = Column(String(12), ForeignKey("tech_items.id", ondelete="CASCADE"), nullable=False)
    edited_by = Column(String(12), ForeignKey("users.id"), nullable=True)
    edited_at = Column(DateTime, default=utcnow)
    summary = Column(Text, default="")

    tech_item = relationship("TechItem", back_populates="history")


# ── Item ↔ Tech link (NEW) ───────────────────────────────────────
#   3번 페이지(연결 찾기): 정책 항목 ↔ 기술 항목 의미 연결
#   예) "오버랩"(PolicyItem) ↔ validate_overlapped_over_lines(TechItem)

class ItemTechLink(Base):
    __tablename__ = "item_tech_links"

    id = Column(String(12), primary_key=True, default=gen_id)
    policy_item_id = Column(String(12), ForeignKey("policy_items.id", ondelete="CASCADE"), nullable=False)
    tech_item_id = Column(String(12), ForeignKey("tech_items.id", ondelete="CASCADE"), nullable=False)
    note = Column(Text, default="")  # 연결 설명 (선택)

    policy_item = relationship("PolicyItem", back_populates="tech_links")


# ── Mapping (Broadcaster ↔ TechItem) ────────────────────────────
#   (기존 그대로 — 테스트 파이프라인용: 방송사별로 어떤 기술항목이 도는가)

class Mapping(Base):
    __tablename__ = "mappings"

    id = Column(String(12), primary_key=True, default=gen_id)
    broadcaster_id = Column(String(12), ForeignKey("broadcasters.id", ondelete="CASCADE"), nullable=False)
    item_id = Column(String(12), ForeignKey("tech_items.id", ondelete="CASCADE"), nullable=False)