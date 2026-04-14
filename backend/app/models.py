import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Text, DateTime, ForeignKey, JSON, Enum as SAEnum
)
from sqlalchemy.orm import relationship
from app.database import Base


def gen_id():
    return uuid.uuid4().hex[:12]


def utcnow():
    return datetime.now(timezone.utc)


# ── Users ────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id = Column(String(12), primary_key=True, default=gen_id)
    username = Column(String(50), unique=True, nullable=False, index=True)
    hashed_password = Column(String(128), nullable=False)
    name = Column(String(100), nullable=False)
    role = Column(String(20), nullable=False)  # admin | dev | subtitle
    created_at = Column(DateTime, default=utcnow)


# ── Broadcasters ─────────────────────────────────────────────────

class Broadcaster(Base):
    __tablename__ = "broadcasters"

    id = Column(String(12), primary_key=True, default=gen_id)
    code = Column(String(30), unique=True, nullable=False)  # e.g. jtbc, tving
    name = Column(String(100), nullable=False)
    color = Column(String(10), default="#6366f1")  # hex color

    policies = relationship("Policy", back_populates="broadcaster")


# ── Policies ─────────────────────────────────────────────────────

class Policy(Base):
    __tablename__ = "policies"

    id = Column(String(12), primary_key=True, default=gen_id)
    broadcaster_id = Column(String(12), ForeignKey("broadcasters.id"), nullable=False)
    title = Column(String(200), nullable=False)
    version = Column(String(20), default="v1.0")
    status = Column(String(20), default="draft")  # active | review | draft
    rules = Column(JSON, default=dict)  # { specs, sync, overlap, lyrics, ... }
    created_by = Column(String(12), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    broadcaster = relationship("Broadcaster", back_populates="policies")
    history = relationship("PolicyHistory", back_populates="policy", order_by="PolicyHistory.edited_at.desc()")


class PolicyHistory(Base):
    __tablename__ = "policy_history"

    id = Column(String(12), primary_key=True, default=gen_id)
    policy_id = Column(String(12), ForeignKey("policies.id", ondelete="CASCADE"), nullable=False)
    edited_by = Column(String(12), ForeignKey("users.id"), nullable=True)
    edited_at = Column(DateTime, default=utcnow)
    summary = Column(Text, default="")

    policy = relationship("Policy", back_populates="history")


# ── Tech Items (Processing / Validation) ─────────────────────────

class TechItem(Base):
    __tablename__ = "tech_items"

    id = Column(String(12), primary_key=True, default=gen_id)
    type = Column(String(20), nullable=False)  # processing | validation
    name = Column(String(200), nullable=False)
    desc = Column(Text, default="")
    params = Column(JSON, default=dict)  # { key: defaultValue, ... }
    scope = Column(String(20), default="common")  # common | specific
    tag = Column(String(20), default="planned")  # in_progress | applied | planned
    source_code = Column(Text, default="")  # 실제 후처리/검증 함수 코드
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


# ── Mapping (Broadcaster ↔ TechItem) ────────────────────────────

class Mapping(Base):
    __tablename__ = "mappings"

    id = Column(String(12), primary_key=True, default=gen_id)
    broadcaster_id = Column(String(12), ForeignKey("broadcasters.id", ondelete="CASCADE"), nullable=False)
    item_id = Column(String(12), ForeignKey("tech_items.id", ondelete="CASCADE"), nullable=False)
