"""
Migration script to add subtitle caching columns to videos table
Version: 003
"""

import sys
import os
from sqlalchemy import text

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import engine


def migrate_up():
    """Add subtitle caching columns to videos table"""
    columns = [
        ("subtitles", "ALTER TABLE videos ADD COLUMN subtitles TEXT NULL;"),
        ("subtitles_detail", "ALTER TABLE videos ADD COLUMN subtitles_detail TEXT NULL;"),
        ("subtitles_output_path", "ALTER TABLE videos ADD COLUMN subtitles_output_path VARCHAR(500) NULL;"),
        ("extraction_request_id", "ALTER TABLE videos ADD COLUMN extraction_request_id VARCHAR(36) NULL;"),
        ("last_extraction_at", "ALTER TABLE videos ADD COLUMN last_extraction_at TIMESTAMP NULL;"),
    ]
    
    # Add each column in a separate transaction
    for col_name, sql in columns:
        try:
            with engine.connect() as conn:
                conn.execute(text(sql))
                conn.commit()
                print(f"✓ Added {col_name} column")
        except Exception as e:
            if "already exists" in str(e) or "duplicate" in str(e).lower():
                print(f"✓ {col_name} column already exists")
            else:
                print(f"✗ Error adding {col_name}: {e}")
                raise

    # Create partial unique index on extraction_request_id
    try:
        with engine.connect() as conn:
            conn.execute(text("""
                CREATE UNIQUE INDEX IF NOT EXISTS idx_extraction_request_id_unique 
                ON videos(id, extraction_request_id) 
                WHERE extraction_request_id IS NOT NULL;
            """))
            conn.commit()
            print("✓ Created partial unique index on extraction_request_id")
    except Exception as e:
        if "already exists" in str(e) or "duplicate" in str(e).lower():
            print("✓ Partial unique index on extraction_request_id already exists")
        else:
            print(f"✗ Error creating index: {e}")
            # Don't raise, as some databases might not support this syntax

    print("\n✓ Migration 003 completed successfully!")


def migrate_down():
    """Remove subtitle caching columns from videos table"""
    with engine.connect() as conn:
        # Drop partial unique index
        try:
            conn.execute(text("""
                DROP INDEX IF EXISTS idx_extraction_request_id_unique;
            """))
            print("✓ Dropped idx_extraction_request_id_unique index")
        except Exception as e:
            if "does not exist" in str(e):
                print("✓ idx_extraction_request_id_unique index doesn't exist")
            else:
                print(f"✗ Error dropping index: {e}")

        # Drop last_extraction_at column
        try:
            conn.execute(text("""
                ALTER TABLE videos 
                DROP COLUMN last_extraction_at;
            """))
            print("✓ Removed last_extraction_at column")
        except Exception as e:
            if "does not exist" in str(e):
                print("✓ last_extraction_at column doesn't exist")
            else:
                print(f"✗ Error removing last_extraction_at: {e}")

        # Drop extraction_request_id column
        try:
            conn.execute(text("""
                ALTER TABLE videos 
                DROP COLUMN extraction_request_id;
            """))
            print("✓ Removed extraction_request_id column")
        except Exception as e:
            if "does not exist" in str(e):
                print("✓ extraction_request_id column doesn't exist")
            else:
                print(f"✗ Error removing extraction_request_id: {e}")

        # Drop subtitles_output_path column
        try:
            conn.execute(text("""
                ALTER TABLE videos 
                DROP COLUMN subtitles_output_path;
            """))
            print("✓ Removed subtitles_output_path column")
        except Exception as e:
            if "does not exist" in str(e):
                print("✓ subtitles_output_path column doesn't exist")
            else:
                print(f"✗ Error removing subtitles_output_path: {e}")

        # Drop subtitles_detail column
        try:
            conn.execute(text("""
                ALTER TABLE videos 
                DROP COLUMN subtitles_detail;
            """))
            print("✓ Removed subtitles_detail column")
        except Exception as e:
            if "does not exist" in str(e):
                print("✓ subtitles_detail column doesn't exist")
            else:
                print(f"✗ Error removing subtitles_detail: {e}")

        # Drop subtitles column
        try:
            conn.execute(text("""
                ALTER TABLE videos 
                DROP COLUMN subtitles;
            """))
            print("✓ Removed subtitles column")
        except Exception as e:
            if "does not exist" in str(e):
                print("✓ subtitles column doesn't exist")
            else:
                print(f"✗ Error removing subtitles: {e}")

        conn.commit()
        print("\n✓ Rollback migration 003 completed!")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Migration script for subtitles caching (v003)")
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
