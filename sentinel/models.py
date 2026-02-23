from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


def utcnow() -> datetime:
    return datetime.now(UTC)


class Contractor(Base):
    __tablename__ = "contractors"

    contractor_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    handle: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        nullable=False,
    )

    submissions: Mapped[list[Submission]] = relationship(back_populates="contractor")


class Case(Base):
    __tablename__ = "cases"

    case_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    priority: Mapped[str] = mapped_column(String(16), nullable=False)
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    deadline_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="OPEN")

    submissions: Mapped[list[Submission]] = relationship(back_populates="case")


class Submission(Base):
    __tablename__ = "submissions"

    submission_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.case_id"), nullable=False)
    contractor_id: Mapped[str] = mapped_column(
        ForeignKey("contractors.contractor_id"),
        nullable=False,
    )
    chain: Mapped[str] = mapped_column(String(8), nullable=False)
    address: Mapped[str] = mapped_column(String(256), nullable=False)
    scam_type: Mapped[str] = mapped_column(String(64), nullable=False)
    source_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    confidence_score: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        nullable=False,
    )
    raw_payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    submission_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    case: Mapped[Case] = relationship(back_populates="submissions")
    contractor: Mapped[Contractor] = relationship(back_populates="submissions")
    events: Mapped[list[SubmissionEvent]] = relationship(back_populates="submission")


class SubmissionEvent(Base):
    __tablename__ = "submission_events"

    event_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    submission_id: Mapped[str] = mapped_column(
        ForeignKey("submissions.submission_id"),
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    event_payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        nullable=False,
    )
    actor: Mapped[str] = mapped_column(String(64), nullable=False)

    submission: Mapped[Submission] = relationship(back_populates="events")
