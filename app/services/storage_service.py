"""Storage service for video file management and quota tracking"""

import os
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List
from sqlalchemy.orm import Session

from .database_service import database_service
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
    ) -> any:
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
        # Get or create user quota
        user_quota = database_service.get_or_create_user_quota(db, user_id)

        # Get current non-deleted video count
        current_count = database_service.get_user_videos_count(db, user_id, include_deleted=False)

        # If at or over limit, delete oldest videos
        if current_count >= settings.MAX_VIDEOS_PER_USER:
            videos_to_delete = current_count - settings.MAX_VIDEOS_PER_USER + 1
            oldest_videos = database_service.get_user_oldest_videos(db, user_id, videos_to_delete)

            for old_video in oldest_videos:
                self._delete_video_files(old_video)
                database_service.soft_delete_video(db, old_video.id, user_id)

            database_service.flush(db)

        # Create new video record
        video = database_service.create_video(
            db=db,
            video_id=video_id,
            user_id=user_id,
            filename=original_filename,
            file_path=file_path,
            file_size=file_size,
        )

        # Refresh user quota with accurate count and size
        database_service.refresh_user_quota(db, user_id)

        database_service.commit(db)
        database_service.refresh(db, video)
        return video

    def get_user_videos(
        self,
        db: Session,
        user_id: str,
        include_deleted: bool = False,
    ) -> List:
        """
        Get all videos for a user.

        Args:
            db: Database session
            user_id: User identifier
            include_deleted: Whether to include soft-deleted videos

        Returns:
            List of Video objects
        """
        return database_service.get_user_videos(db, user_id, include_deleted)

    def get_video(
        self,
        db: Session,
        video_id: str,
        user_id: Optional[str] = None,
    ) -> Optional:
        """
        Get a specific video by ID.

        Args:
            db: Database session
            video_id: Video GUID
            user_id: Optional user ID for permission check

        Returns:
            Video object or None if not found
        """
        return database_service.get_video_by_id(db, video_id, user_id, include_deleted=False)

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
        # Get video to delete
        video = database_service.get_video_by_id(db, video_id, user_id, include_deleted=False)

        if not video:
            return False

        if hard_delete:
            self._delete_video_files(video)

        # Soft delete the video
        database_service.soft_delete_video(db, video_id, user_id)
        database_service.flush(db)

        # Update quota with accurate count
        database_service.refresh_user_quota(db, user_id)

        database_service.commit(db)
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
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        old_deleted_videos = database_service.get_deleted_videos_by_cutoff_date(db, cutoff_date)

        count = 0
        for video in old_deleted_videos:
            self._delete_video_files(video)
            database_service.hard_delete_video(db, video.id)
            count += 1

        database_service.commit(db)
        return count

    def get_user_quota(self, db: Session, user_id: str) -> Optional:
        """
        Get user quota information.

        Args:
            db: Database session
            user_id: User identifier

        Returns:
            UserQuota object or None
        """
        return database_service.get_user_quota(db, user_id)


# Singleton instance
storage_service = StorageService()
