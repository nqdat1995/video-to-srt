"""SQLAlchemy ORM models for database tables"""

from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, DateTime, Boolean, Index
from ..core.database import Base


class Video(Base):
    """Video metadata model"""
    __tablename__ = "videos"

    id = Column(String(36), primary_key=True, unique=True, index=True)  # GUID
    user_id = Column(String(36), index=True, nullable=False)  # User identifier (can be GUID or session ID)
    filename = Column(String(255), nullable=False)  # Original uploaded filename
    file_path = Column(String(500), nullable=False, unique=True)  # Path on disk
    file_size = Column(Integer, nullable=False)  # Size in bytes
    is_deleted = Column(Boolean, default=False, nullable=False)  # Soft delete flag
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    deleted_at = Column(DateTime, nullable=True)  # Timestamp when marked as deleted
    
    __table_args__ = (
        Index("idx_user_id_created_at", "user_id", "created_at"),
        Index("idx_user_id_is_deleted", "user_id", "is_deleted"),
    )

    def __repr__(self):
        return f"<Video(id={self.id}, user_id={self.user_id}, filename={self.filename}, is_deleted={self.is_deleted})>"


class UserQuota(Base):
    """User upload quota tracking model"""
    __tablename__ = "user_quotas"

    user_id = Column(String(36), primary_key=True, unique=True, index=True)
    video_count = Column(Integer, default=0, nullable=False)  # Count of non-deleted videos
    total_size_bytes = Column(Integer, default=0, nullable=False)  # Total size of non-deleted videos
    last_updated = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("idx_last_updated", "last_updated"),
    )

    def __repr__(self):
        return f"<UserQuota(user_id={self.user_id}, video_count={self.video_count}, total_size_bytes={self.total_size_bytes})>"
