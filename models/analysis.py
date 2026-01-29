"""
Analysis Result Model
"""
import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Text, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB

from db.session import Base


class AnalysisResult(Base):
    """AI analysis result for a filing."""
    
    __tablename__ = "analysis_results"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    filing_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("filings.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )
    model_used: Mapped[str] = mapped_column(
        String(100),
        nullable=True
    )
    analysis_text: Mapped[str] = mapped_column(
        Text,
        nullable=True
    )
    sentiment: Mapped[str] = mapped_column(
        String(20),
        nullable=True  # bullish, bearish, neutral
    )
    key_findings: Mapped[dict] = mapped_column(
        JSONB,
        nullable=True
    )
    tokens_used: Mapped[int] = mapped_column(
        Integer,
        nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow
    )
    
    # Relationships
    filing = relationship("Filing", back_populates="analysis_results")
    user = relationship("User", back_populates="analysis_results")
    
    def __repr__(self) -> str:
        return f"<AnalysisResult {self.filing_id} {self.sentiment}>"
