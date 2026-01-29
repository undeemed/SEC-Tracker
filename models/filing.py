"""
SEC Filing Model
"""
import uuid
from datetime import datetime, date
from sqlalchemy import String, Date, DateTime, Text, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from db.session import Base


class Filing(Base):
    """SEC filing record."""
    
    __tablename__ = "filings"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    ticker: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        index=True
    )
    cik: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True
    )
    accession_number: Mapped[str] = mapped_column(
        String(30),
        unique=True,
        nullable=False,
        index=True
    )
    form_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True
    )
    filing_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True
    )
    description: Mapped[str] = mapped_column(
        Text,
        nullable=True
    )
    document_url: Mapped[str] = mapped_column(
        Text,
        nullable=True
    )
    raw_content: Mapped[str] = mapped_column(
        Text,
        nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow
    )
    
    # Relationships
    transactions = relationship("Form4Transaction", back_populates="filing", cascade="all, delete-orphan")
    analysis_results = relationship("AnalysisResult", back_populates="filing", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index("idx_filings_ticker_form", "ticker", "form_type"),
        Index("idx_filings_date_form", "filing_date", "form_type"),
    )
    
    def __repr__(self) -> str:
        return f"<Filing {self.ticker} {self.form_type} {self.filing_date}>"
