"""
Tracking Job Model
"""
import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Text, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB

from db.session import Base


class TrackingJob(Base):
    """Async tracking job record."""
    
    __tablename__ = "tracking_jobs"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    job_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False  # track, analyze, refresh
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="queued",
        index=True  # queued, processing, complete, failed
    )
    ticker: Mapped[str] = mapped_column(
        String(10),
        nullable=True
    )
    progress: Mapped[int] = mapped_column(
        Integer,
        default=0  # 0-100
    )
    message: Mapped[str] = mapped_column(
        Text,
        nullable=True
    )
    result: Mapped[dict] = mapped_column(
        JSONB,
        nullable=True
    )
    error: Mapped[str] = mapped_column(
        Text,
        nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    
    # Relationships
    user = relationship("User", back_populates="tracking_jobs")
    
    def __repr__(self) -> str:
        return f"<TrackingJob {self.id} {self.job_type} {self.status}>"
