"""Storage service for video file management and quota tracking"""

import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc, func

from ..models.database import Video, UserQuota
from ..core.config import settings


class StorageService:
    """Handles video storage, quota management, and cleanup"""

    def __init__(self):
        self.upload_dir = Path(settings.UPLOAD_DIR)
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    def save_video(
        self,
        db: Session,
        video_id: str,
        user_id: str,
        file_path: str,
        original_filename: str,
        file_size: int,
    ) -> Video:
        """
        Save video metadata to database and handle quota management.
        
        If user exceeds MAX_VIDEOS_PER_USER, automatically delete oldest videos.

        Args:
            db: Database session
            video_id: GUID for the video
            user_id: User identifier
            file_path: Full path where video is saved on disk
            original_filename: Original uploaded filename
            file_size: File size in bytes

        Returns:
            Video object saved to database
        """
        # Check if user exists in quota table
        user_quota = db.query(UserQuota).filter(
            UserQuota.user_id == user_id
        ).first()

        if not user_quota:
            user_quota = UserQuota(user_id=user_id, video_count=0, total_size_bytes=0)
            db.add(user_quota)
            db.flush()

        # Get current non-deleted video count
        current_count = db.query(Video).filter(
            and_(
                Video.user_id == user_id,
                Video.is_deleted == False
            )
        ).count()

        # If at or over limit, delete oldest videos
        if current_count >= settings.MAX_VIDEOS_PER_USER:
            videos_to_delete = current_count - settings.MAX_VIDEOS_PER_USER + 1
            oldest_videos = db.query(Video).filter(
                and_(
                    Video.user_id == user_id,
                    Video.is_deleted == False
                )
            ).order_by(Video.created_at).limit(videos_to_delete).all()

            for old_video in oldest_videos:
                self._delete_video_files(old_video)
                old_video.is_deleted = True
                old_video.deleted_at = datetime.utcnow()
                # Deduct from quota
                user_quota.video_count = max(0, user_quota.video_count - 1)
                user_quota.total_size_bytes = max(0, user_quota.total_size_bytes - old_video.file_size)
            db.flush()

        # Create new video record
        video = Video(
            id=video_id,
            user_id=user_id,
            filename=original_filename,
            file_path=file_path,
            file_size=file_size,
            is_deleted=False,
            created_at=datetime.utcnow(),
        )
        db.add(video)
        db.flush()

        # Update user quota with accurate count
        user_quota.video_count = db.query(Video).filter(
            and_(
                Video.user_id == user_id,
                Video.is_deleted == False
            )
        ).count()
        user_quota.total_size_bytes = db.query(Video).filter(
            and_(
                Video.user_id == user_id,
                Video.is_deleted == False
            )
        ).with_entities(func.sum(Video.file_size)).scalar() or 0
        user_quota.last_updated = datetime.utcnow()

        db.commit()
        db.refresh(video)
        return video

    def get_user_videos(
        self,
        db: Session,
        user_id: str,
        include_deleted: bool = False,
    ) -> List[Video]:
        """
        Get all videos for a user.

        Args:
            db: Database session
            user_id: User identifier
            include_deleted: Whether to include soft-deleted videos

        Returns:
            List of Video objects
        """
        query = db.query(Video).filter(Video.user_id == user_id)

        if not include_deleted:
            query = query.filter(Video.is_deleted == False)

        return query.order_by(desc(Video.created_at)).all()

    def get_video(
        self,
        db: Session,
        video_id: str,
        user_id: Optional[str] = None,
    ) -> Optional[Video]:
        """
        Get a specific video by ID.

        Args:
            db: Database session
            video_id: Video GUID
            user_id: Optional user ID for permission check

        Returns:
            Video object or None if not found
        """
        query = db.query(Video).filter(Video.id == video_id)

        if user_id:
            query = query.filter(Video.user_id == user_id)

        return query.first()

    def delete_video(
        self,
        db: Session,
        video_id: str,
        user_id: str,
        hard_delete: bool = False,
    ) -> bool:
        """
        Delete a video (soft delete by default).

        Args:
            db: Database session
            video_id: Video GUID
            user_id: User identifier for permission check
            hard_delete: If True, delete file from disk; if False, just set is_deleted flag

        Returns:
            True if successful, False otherwise
        """
        video = db.query(Video).filter(
            and_(
                Video.id == video_id,
                Video.user_id == user_id,
            )
        ).first()

        if not video:
            return False

        if hard_delete:
            self._delete_video_files(video)

        video.is_deleted = True
        video.deleted_at = datetime.utcnow()
        db.flush()

        # Update quota with accurate count
        user_quota = db.query(UserQuota).filter(
            UserQuota.user_id == user_id
        ).first()

        if user_quota:
            user_quota.video_count = db.query(Video).filter(
                and_(
                    Video.user_id == user_id,
                    Video.is_deleted == False
                )
            ).count()
            user_quota.total_size_bytes = db.query(Video).filter(
                and_(
                    Video.user_id == user_id,
                    Video.is_deleted == False
                )
            ).with_entities(func.sum(Video.file_size)).scalar() or 0
            user_quota.last_updated = datetime.utcnow()

        db.commit()
        return True

    def _delete_video_files(self, video: Video) -> None:
        """
        Delete video file from disk.

        Args:
            video: Video object with file_path
        """
        try:
            file_path = Path(video.file_path)
            if file_path.exists():
                file_path.unlink()
        except Exception as e:
            # Log error but don't raise to avoid breaking the soft-delete operation
            import logging
            logging.warning(f"Failed to delete video file {video.file_path}: {str(e)}")

    def cleanup_deleted_videos(self, db: Session, days: int = 30) -> int:
        """
        Hard-delete videos marked as deleted for more than N days.

        Args:
            db: Database session
            days: Number of days to keep deleted videos

        Returns:
            Number of videos cleaned up
        """
        cutoff_date = datetime.utcnow() - datetime.timedelta(days=days)
        old_deleted_videos = db.query(Video).filter(
            and_(
                Video.is_deleted == True,
                Video.deleted_at <= cutoff_date,
            )
        ).all()

        count = 0
        for video in old_deleted_videos:
            self._delete_video_files(video)
            db.delete(video)
            count += 1

        db.commit()
        return count

    def get_user_quota(self, db: Session, user_id: str) -> Optional[UserQuota]:
        """
        Get user quota information.

        Args:
            db: Database session
            user_id: User identifier

        Returns:
            UserQuota object or None
        """
        return db.query(UserQuota).filter(
            UserQuota.user_id == user_id
        ).first()


# Singleton instance
storage_service = StorageService()
