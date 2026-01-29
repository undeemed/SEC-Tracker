"""
User Watchlist Model
"""
import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from db.session import Base


class UserWatchlist(Base):
    """User's tracked companies."""
    
    __tablename__ = "user_watchlists"
    
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
    ticker: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        index=True
    )
    cik: Mapped[str] = mapped_column(
        String(20),
        nullable=True
    )
    company_name: Mapped[str] = mapped_column(
        String(255),
        nullable=True
    )
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow
    )
    
    # Relationships
    user = relationship("User", back_populates="watchlist")
    
    # Unique constraint: user can only watch each ticker once
    __table_args__ = (
        {"sqlite_autoincrement": True},
    )
    
    def __repr__(self) -> str:
        return f"<UserWatchlist {self.ticker} for user {self.user_id}>"
