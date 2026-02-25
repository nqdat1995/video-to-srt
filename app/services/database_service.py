"""Database service layer for all database operations"""

from datetime import datetime, timedelta
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc, func

from ..models.database import Video, UserQuota


class DatabaseService:
    """Handles all database operations for videos and user quotas"""

    # ============= Video Operations =============

    def create_video(
        self,
        db: Session,
        video_id: str,
        user_id: str,
        filename: str,
        file_path: str,
        file_size: int,
    ) -> Video:
        """
        Create a new video record in the database.

        Args:
            db: Database session
            video_id: GUID for the video
            user_id: User identifier
            filename: Original uploaded filename
            file_path: Full path where video is saved on disk
            file_size: File size in bytes

        Returns:
            Video object
        """
        video = Video(
            id=video_id,
            user_id=user_id,
            filename=filename,
            file_path=file_path,
            file_size=file_size,
            is_deleted=False,
            created_at=datetime.utcnow(),
        )
        db.add(video)
        db.flush()
        return video

    def get_video_by_id(
        self,
        db: Session,
        video_id: str,
        user_id: Optional[str] = None,
        include_deleted: bool = False,
    ) -> Optional[Video]:
        """
        Get a specific video by ID.

        Args:
            db: Database session
            video_id: Video GUID
            user_id: Optional user ID for permission check
            include_deleted: Whether to include soft-deleted videos

        Returns:
            Video object or None if not found
        """
        query = db.query(Video).filter(Video.id == video_id)

        if user_id:
            query = query.filter(Video.user_id == user_id)

        if not include_deleted:
            query = query.filter(Video.is_deleted == False)

        return query.first()

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
            List of Video objects sorted by created_at descending
        """
        query = db.query(Video).filter(Video.user_id == user_id)

        if not include_deleted:
            query = query.filter(Video.is_deleted == False)

        return query.order_by(desc(Video.created_at)).all()

    def get_user_videos_count(
        self,
        db: Session,
        user_id: str,
        include_deleted: bool = False,
    ) -> int:
        """
        Get count of videos for a user.

        Args:
            db: Database session
            user_id: User identifier
            include_deleted: Whether to include soft-deleted videos

        Returns:
            Count of videos
        """
        query = db.query(Video).filter(Video.user_id == user_id)

        if not include_deleted:
            query = query.filter(Video.is_deleted == False)

        return query.count()

    def get_user_oldest_videos(
        self,
        db: Session,
        user_id: str,
        limit: int,
    ) -> List[Video]:
        """
        Get oldest non-deleted videos for a user.

        Args:
            db: Database session
            user_id: User identifier
            limit: Maximum number of videos to return

        Returns:
            List of oldest Video objects
        """
        return db.query(Video).filter(
            and_(
                Video.user_id == user_id,
                Video.is_deleted == False
            )
        ).order_by(Video.created_at).limit(limit).all()

    def get_user_total_size(
        self,
        db: Session,
        user_id: str,
        include_deleted: bool = False,
    ) -> int:
        """
        Get total size of videos for a user.

        Args:
            db: Database session
            user_id: User identifier
            include_deleted: Whether to include soft-deleted videos

        Returns:
            Total size in bytes
        """
        query = db.query(Video).filter(Video.user_id == user_id)

        if not include_deleted:
            query = query.filter(Video.is_deleted == False)

        total = query.with_entities(func.sum(Video.file_size)).scalar()
        return total or 0

    def soft_delete_video(
        self,
        db: Session,
        video_id: str,
        user_id: str,
    ) -> bool:
        """
        Mark a video as deleted (soft delete).

        Args:
            db: Database session
            video_id: Video GUID
            user_id: User identifier for permission check

        Returns:
            True if successful, False if not found
        """
        video = db.query(Video).filter(
            and_(
                Video.id == video_id,
                Video.user_id == user_id,
            )
        ).first()

        if not video:
            return False

        video.is_deleted = True
        video.deleted_at = datetime.utcnow()
        db.flush()
        return True

    def hard_delete_video(
        self,
        db: Session,
        video_id: str,
    ) -> bool:
        """
        Permanently delete a video record from database.

        Args:
            db: Database session
            video_id: Video GUID

        Returns:
            True if successful, False if not found
        """
        video = db.query(Video).filter(Video.id == video_id).first()

        if not video:
            return False

        db.delete(video)
        db.flush()
        return True

    def get_deleted_videos_by_cutoff_date(
        self,
        db: Session,
        cutoff_date: datetime,
    ) -> List[Video]:
        """
        Get videos deleted before a certain date.

        Args:
            db: Database session
            cutoff_date: Date cutoff for deleted videos

        Returns:
            List of deleted Video objects
        """
        return db.query(Video).filter(
            and_(
                Video.is_deleted == True,
                Video.deleted_at <= cutoff_date,
            )
        ).all()

    # ============= User Quota Operations =============

    def get_or_create_user_quota(
        self,
        db: Session,
        user_id: str,
    ) -> UserQuota:
        """
        Get existing user quota or create a new one.

        Args:
            db: Database session
            user_id: User identifier

        Returns:
            UserQuota object
        """
        user_quota = db.query(UserQuota).filter(
            UserQuota.user_id == user_id
        ).first()

        if not user_quota:
            user_quota = UserQuota(
                user_id=user_id,
                video_count=0,
                total_size_bytes=0
            )
            db.add(user_quota)
            db.flush()

        return user_quota

    def get_user_quota(
        self,
        db: Session,
        user_id: str,
    ) -> Optional[UserQuota]:
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

    def update_user_quota(
        self,
        db: Session,
        user_id: str,
        video_count: Optional[int] = None,
        total_size_bytes: Optional[int] = None,
    ) -> UserQuota:
        """
        Update user quota information.

        Args:
            db: Database session
            user_id: User identifier
            video_count: New video count (or None to keep current)
            total_size_bytes: New total size (or None to keep current)

        Returns:
            Updated UserQuota object
        """
        user_quota = self.get_or_create_user_quota(db, user_id)

        if video_count is not None:
            user_quota.video_count = video_count

        if total_size_bytes is not None:
            user_quota.total_size_bytes = total_size_bytes

        user_quota.last_updated = datetime.utcnow()
        db.flush()

        return user_quota

    def refresh_user_quota(
        self,
        db: Session,
        user_id: str,
    ) -> UserQuota:
        """
        Recalculate user quota based on current videos.

        Args:
            db: Database session
            user_id: User identifier

        Returns:
            Updated UserQuota object
        """
        user_quota = self.get_or_create_user_quota(db, user_id)

        # Recalculate video count and total size
        video_count = self.get_user_videos_count(db, user_id, include_deleted=False)
        total_size = self.get_user_total_size(db, user_id, include_deleted=False)

        user_quota.video_count = video_count
        user_quota.total_size_bytes = total_size
        user_quota.last_updated = datetime.utcnow()
        db.flush()

        return user_quota

    # ============= Batch Operations =============

    def commit(self, db: Session) -> None:
        """
        Commit all pending database changes.

        Args:
            db: Database session
        """
        db.commit()

    def flush(self, db: Session) -> None:
        """
        Flush pending changes without committing.

        Args:
            db: Database session
        """
        db.flush()

    def refresh(self, db: Session, obj: any) -> None:
        """
        Refresh object from database.

        Args:
            db: Database session
            obj: Database object to refresh
        """
        db.refresh(obj)


# Singleton instance
database_service = DatabaseService()
