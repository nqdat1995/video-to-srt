"""SQLAlchemy ORM models for database tables"""

import json
from datetime import datetime
from typing import List, Optional
from sqlalchemy import Column, String, Integer, Float, DateTime, Boolean, Index, Text
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
    
    # Subtitle caching columns
    subtitles = Column(Text, nullable=True)  # Full SRT content
    subtitles_detail = Column(Text, nullable=True)  # JSON string of SrtDetail list
    subtitles_output_path = Column(String(500), nullable=True)  # Path to saved SRT file
    extraction_request_id = Column(String(36), nullable=True)  # Tracks active extraction
    last_extraction_at = Column(DateTime, nullable=True)  # Cache timestamp
    
    __table_args__ = (
        Index("idx_video_user_id_created_at", "user_id", "created_at"),
        Index("idx_video_user_id_is_deleted", "user_id", "is_deleted"),
    )

    def __repr__(self):
        return f"<Video(id={self.id}, user_id={self.user_id}, filename={self.filename}, is_deleted={self.is_deleted})>"

    def serialize_srt_details(self, srt_detail_list: List) -> str:
        """
        Serialize a list of SrtDetail objects to JSON string.
        
        Args:
            srt_detail_list: List of SrtDetail Pydantic models
            
        Returns:
            JSON string representation of the list
        """
        if not srt_detail_list:
            return "[]"
        
        serialized = [detail.model_dump() for detail in srt_detail_list]
        return json.dumps(serialized, ensure_ascii=False)

    def deserialize_srt_details(self, json_string: Optional[str]) -> List:
        """
        Deserialize a JSON string back to list of SrtDetail dictionaries.
        
        Args:
            json_string: JSON string from subtitles_detail column
            
        Returns:
            List of SrtDetail dictionaries, or empty list if None/invalid
        """
        if not json_string:
            return []
        
        try:
            return json.loads(json_string)
        except (json.JSONDecodeError, TypeError):
            return []


class Audio(Base):
    """Audio metadata model for TTS-generated audio files"""
    __tablename__ = "audios"

    id = Column(String(36), primary_key=True, unique=True, index=True)  # GUID
    user_id = Column(String(36), index=True, nullable=False)  # User identifier
    filename = Column(String(255), nullable=False)  # Original audio filename
    file_path = Column(String(500), nullable=False, unique=True)  # Path on disk
    file_size = Column(Integer, nullable=False)  # Size in bytes
    duration_ms = Column(Float, nullable=True)  # Duration in milliseconds
    is_deleted = Column(Boolean, default=False, nullable=False)  # Soft delete flag
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    deleted_at = Column(DateTime, nullable=True)  # Timestamp when marked as deleted
    
    __table_args__ = (
        Index("idx_audio_user_id_created_at", "user_id", "created_at"),
        Index("idx_audio_user_id_is_deleted", "user_id", "is_deleted"),
    )

    def __repr__(self):
        return f"<Audio(id={self.id}, user_id={self.user_id}, filename={self.filename}, is_deleted={self.is_deleted})>"


class UserQuota(Base):
    """User upload quota tracking model"""
    __tablename__ = "user_quotas"

    user_id = Column(String(36), primary_key=True, unique=True, index=True)
    video_count = Column(Integer, default=0, nullable=False)  # Count of non-deleted videos
    total_size_bytes = Column(Integer, default=0, nullable=False)  # Total size of non-deleted videos
    audio_count = Column(Integer, default=0, nullable=False)  # Count of non-deleted audios
    audio_total_size_bytes = Column(Integer, default=0, nullable=False)  # Total size of non-deleted audios
    last_updated = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("idx_last_updated", "last_updated"),
    )

    def __repr__(self):
        return f"<UserQuota(user_id={self.user_id}, video_count={self.video_count}, total_size_bytes={self.total_size_bytes}, audio_count={self.audio_count}, audio_total_size_bytes={self.audio_total_size_bytes})>"
