"""
Migration script to create initial database schema
This creates the main tables: videos, audios, and user_quotas
"""

import sys
import os
from sqlalchemy import text
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import engine


def migrate_up():
    """Create initial schema tables"""
    with engine.connect() as conn:
        # Create videos table
        try:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS videos (
                    id VARCHAR(36) PRIMARY KEY UNIQUE NOT NULL,
                    user_id VARCHAR(36) NOT NULL,
                    filename VARCHAR(255) NOT NULL,
                    file_path VARCHAR(500) NOT NULL UNIQUE,
                    file_size INTEGER NOT NULL,
                    is_deleted BOOLEAN DEFAULT false NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                    deleted_at TIMESTAMP NULL
                );
                
                CREATE INDEX IF NOT EXISTS idx_videos_user_id ON videos(user_id);
                CREATE INDEX IF NOT EXISTS idx_videos_created_at ON videos(created_at);
                CREATE INDEX IF NOT EXISTS idx_video_user_id_created_at ON videos(user_id, created_at);
                CREATE INDEX IF NOT EXISTS idx_video_user_id_is_deleted ON videos(user_id, is_deleted);
            """))
            print("✓ Created videos table")
        except Exception as e:
            if "already exists" not in str(e).lower():
                print(f"✗ Error creating videos table: {e}")
                raise

        # Create audios table
        try:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS audios (
                    id VARCHAR(36) PRIMARY KEY UNIQUE NOT NULL,
                    user_id VARCHAR(36) NOT NULL,
                    filename VARCHAR(255) NOT NULL,
                    file_path VARCHAR(500) NOT NULL UNIQUE,
                    file_size INTEGER NOT NULL,
                    duration_ms FLOAT NULL,
                    is_deleted BOOLEAN DEFAULT false NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                    deleted_at TIMESTAMP NULL
                );
                
                CREATE INDEX IF NOT EXISTS idx_audios_user_id ON audios(user_id);
                CREATE INDEX IF NOT EXISTS idx_audios_created_at ON audios(created_at);
                CREATE INDEX IF NOT EXISTS idx_audio_user_id_created_at ON audios(user_id, created_at);
                CREATE INDEX IF NOT EXISTS idx_audio_user_id_is_deleted ON audios(user_id, is_deleted);
            """))
            print("✓ Created audios table")
        except Exception as e:
            if "already exists" not in str(e).lower():
                print(f"✗ Error creating audios table: {e}")
                raise

        # Create user_quotas table
        try:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS user_quotas (
                    user_id VARCHAR(36) PRIMARY KEY UNIQUE NOT NULL,
                    video_count INTEGER DEFAULT 0 NOT NULL,
                    total_size_bytes INTEGER DEFAULT 0 NOT NULL,
                    audio_count INTEGER DEFAULT 0 NOT NULL,
                    audio_total_size_bytes INTEGER DEFAULT 0 NOT NULL,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
                );
                
                CREATE INDEX IF NOT EXISTS idx_user_quotas_last_updated ON user_quotas(last_updated);
            """))
            print("✓ Created user_quotas table")
        except Exception as e:
            if "already exists" not in str(e).lower():
                print(f"✗ Error creating user_quotas table: {e}")
                raise

        conn.commit()
        print("\n✓ Initial schema migration completed successfully!")


def migrate_down():
    """Drop all tables (rollback initial schema)"""
    with engine.connect() as conn:
        try:
            conn.execute(text("""
                DROP TABLE IF EXISTS user_quotas CASCADE;
                DROP TABLE IF EXISTS audios CASCADE;
                DROP TABLE IF EXISTS videos CASCADE;
            """))
            print("✓ Dropped all tables")
        except Exception as e:
            print(f"✗ Error dropping tables: {e}")
            raise

        conn.commit()
        print("\n✓ Rollback completed!")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Migration script for initial schema")
    parser.add_argument(
        "direction",
        choices=["up", "down"],
        help="Migration direction: 'up' to apply, 'down' to rollback"
    )
    
    args = parser.parse_args()
    
    if args.direction == "up":
        migrate_up()
    else:
        migrate_down()
