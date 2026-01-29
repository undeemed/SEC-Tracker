"""
Form 4 Transaction Model
"""
import uuid
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import String, Date, DateTime, Boolean, Numeric, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from db.session import Base


class Form4Transaction(Base):
    """Form 4 insider trading transaction."""
    
    __tablename__ = "form4_transactions"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    filing_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("filings.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )
    ticker: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        index=True
    )
    company_name: Mapped[str] = mapped_column(
        String(255),
        nullable=True
    )
    owner_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True
    )
    role: Mapped[str] = mapped_column(
        String(100),
        nullable=True
    )
    transaction_type: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        index=True  # buy, sell, grant, etc.
    )
    is_planned: Mapped[bool] = mapped_column(
        Boolean,
        default=False
    )
    shares: Mapped[Decimal] = mapped_column(
        Numeric(20, 4),
        nullable=True
    )
    price: Mapped[Decimal] = mapped_column(
        Numeric(20, 4),
        nullable=True
    )
    amount: Mapped[Decimal] = mapped_column(
        Numeric(20, 2),
        nullable=True
    )
    transaction_date: Mapped[date] = mapped_column(
        Date,
        nullable=True,
        index=True
    )
    filing_date: Mapped[date] = mapped_column(
        Date,
        nullable=True
    )
    accession_number: Mapped[str] = mapped_column(
        String(30),
        nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow
    )
    
    # Relationships
    filing = relationship("Filing", back_populates="transactions")
    
    # Indexes
    __table_args__ = (
        Index("idx_transactions_ticker_date", "ticker", "transaction_date"),
        Index("idx_transactions_type_date", "transaction_type", "transaction_date"),
    )
    
    def __repr__(self) -> str:
        return f"<Form4Transaction {self.ticker} {self.owner_name} {self.transaction_type}>"
