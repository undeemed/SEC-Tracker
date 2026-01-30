"""
User Model
"""
import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from db.session import Base


class User(Base):
    """User account model."""
    
    __tablename__ = "users"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True
    )
    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )
    # DEPRECATED: plaintext API key storage - use api_key_hash instead
    api_key: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=True,
        index=True
    )
    # SECURITY: SHA-256 hash of API key (64 hex chars)
    api_key_hash: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=True,
        index=True
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )
    
    # Relationships
    watchlist = relationship("UserWatchlist", back_populates="user", cascade="all, delete-orphan")
    analysis_results = relationship("AnalysisResult", back_populates="user", cascade="all, delete-orphan")
    tracking_jobs = relationship("TrackingJob", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<User {self.email}>"

    @property
    def has_api_key(self) -> bool:
        """Whether the user currently has an API key configured."""
        return bool(self.api_key_hash or self.api_key)
