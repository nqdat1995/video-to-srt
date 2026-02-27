"""Database configuration and session management"""

from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import declarative_base, sessionmaker
from .config import settings

# Create database engine
engine = create_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

# Create session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

# Create declarative base for models
Base = declarative_base()


def get_db():
    """Dependency function to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _migrate_user_quotas_schema():
    """Migrate user_quotas table to add audio quota columns if they don't exist"""
    try:
        inspector = inspect(engine)
        
        # Check if user_quotas table exists
        if 'user_quotas' not in inspector.get_table_names():
            return  # Table doesn't exist yet, will be created by init_db
        
        # Get existing columns
        columns = {col['name'] for col in inspector.get_columns('user_quotas')}
        
        with engine.connect() as conn:
            # Add audio_count column if missing
            if 'audio_count' not in columns:
                try:
                    conn.execute(text("""
                        ALTER TABLE user_quotas 
                        ADD COLUMN audio_count INTEGER DEFAULT 0 NOT NULL;
                    """))
                    print("✓ Added audio_count column to user_quotas")
                except Exception as e:
                    if "already exists" not in str(e).lower():
                        print(f"⚠ Could not add audio_count: {e}")
            
            # Add audio_total_size_bytes column if missing
            if 'audio_total_size_bytes' not in columns:
                try:
                    conn.execute(text("""
                        ALTER TABLE user_quotas 
                        ADD COLUMN audio_total_size_bytes INTEGER DEFAULT 0 NOT NULL;
                    """))
                    print("✓ Added audio_total_size_bytes column to user_quotas")
                except Exception as e:
                    if "already exists" not in str(e).lower():
                        print(f"⚠ Could not add audio_total_size_bytes: {e}")
            
            conn.commit()
    except Exception as e:
        print(f"⚠ Migration warning: {e}")


def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)
    # Run schema migrations
    _migrate_user_quotas_schema()
