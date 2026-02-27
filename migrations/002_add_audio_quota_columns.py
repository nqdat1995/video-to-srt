"""
Migration script to add audio quota columns to user_quotas table
Version: 002
"""

import sys
import os
from sqlalchemy import text
from sqlalchemy.orm import Session

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import engine
from app.models.database import UserQuota


def migrate_up():
    """Add audio quota columns to user_quotas table"""
    with engine.connect() as conn:
        # Add audio_count column
        try:
            conn.execute(text("""
                ALTER TABLE user_quotas 
                ADD COLUMN audio_count INTEGER DEFAULT 0 NOT NULL;
            """))
            print("✓ Added audio_count column")
        except Exception as e:
            if "already exists" in str(e) or "duplicate" in str(e).lower():
                print("✓ audio_count column already exists")
            else:
                print(f"✗ Error adding audio_count: {e}")
                raise

        # Add audio_total_size_bytes column
        try:
            conn.execute(text("""
                ALTER TABLE user_quotas 
                ADD COLUMN audio_total_size_bytes INTEGER DEFAULT 0 NOT NULL;
            """))
            print("✓ Added audio_total_size_bytes column")
        except Exception as e:
            if "already exists" in str(e) or "duplicate" in str(e).lower():
                print("✓ audio_total_size_bytes column already exists")
            else:
                print(f"✗ Error adding audio_total_size_bytes: {e}")
                raise

        conn.commit()
        print("\n✓ Migration 002 completed successfully!")


def migrate_down():
    """Remove audio quota columns from user_quotas table"""
    with engine.connect() as conn:
        # Remove audio_total_size_bytes column
        try:
            conn.execute(text("""
                ALTER TABLE user_quotas 
                DROP COLUMN audio_total_size_bytes;
            """))
            print("✓ Removed audio_total_size_bytes column")
        except Exception as e:
            if "does not exist" in str(e):
                print("✓ audio_total_size_bytes column doesn't exist")
            else:
                print(f"✗ Error removing audio_total_size_bytes: {e}")

        # Remove audio_count column
        try:
            conn.execute(text("""
                ALTER TABLE user_quotas 
                DROP COLUMN audio_count;
            """))
            print("✓ Removed audio_count column")
        except Exception as e:
            if "does not exist" in str(e):
                print("✓ audio_count column doesn't exist")
            else:
                print(f"✗ Error removing audio_count: {e}")

        conn.commit()
        print("\n✓ Rollback migration 002 completed!")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Migration script for user_quotas table (v002)")
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
