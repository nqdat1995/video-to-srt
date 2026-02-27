# Database Setup & Migrations

## 📋 Tổng quan

Dự án sử dụng **PostgreSQL 16** với hệ thống migration thủ công. Cần phải chạy migrations để tạo các table cần thiết.

## ⚙️ Các Table Cần Thiết

### 1. `videos` - Video uploads metadata
- Stores metadata của videos được upload
- Soft delete support (không xóa thực)
- Indexed by user_id, created_at, is_deleted

### 2. `audios` - Audio files metadata  
- Stores metadata của TTS-generated audio
- Soft delete support
- Indexed by user_id, created_at, is_deleted

### 3. `user_quotas` - User storage quota tracking
- Tracks dung lượng per user (videos + audios)
- Auto-update khi upload/delete
- Prevent exceed storage limits

## 🚀 Quick Start

### 1. Setup PostgreSQL

```bash
# Create database (nếu chưa có)
createdb video_to_srt

# Or using psql
psql -U postgres
CREATE DATABASE video_to_srt;
```

### 2. Configure Database URL

Edit `.env` hoặc `app/core/config.py`:
```bash
DATABASE_URL=postgresql://user:password@localhost:5432/video_to_srt
```

### 3. Run Migrations

```bash
cd d:\LEARN\video-to-srt

# Run tất cả migrations
python migrations/migrate.py up

# Hoặc chạy riêng
python migrations/001_initial_schema.py up
python migrations/002_add_audio_quota_columns.py up
```

### 4. Verify Setup

```bash
# Check tables created
psql -U postgres -d video_to_srt -c "\dt"

# Output should show:
# videos | table
# audios | table  
# user_quotas | table

# Check table structure
psql -U postgres -d video_to_srt -c "\d videos"
psql -U postgres -d video_to_srt -c "\d audios"
psql -U postgres -d video_to_srt -c "\d user_quotas"
```

## 📁 Migration Files

### Trong `migrations/` folder

| File | Mục đích | Status |
|------|---------|--------|
| `001_initial_schema.py` | Create tables (videos, audios, user_quotas) | ✅ Active |
| `002_add_audio_quota_columns.py` | Add audio quota columns to user_quotas | ✅ Active |
| `migrate.py` | Migration runner script | ✅ Active |
| `add_audio_quota_columns.py` | ❌ OLD - use 002_* instead | **DEPRECATED** |

## 📊 Database Schema

### Quick View

```
videos table:
├── id (GUID, PK)
├── user_id (FK reference)
├── filename, file_path, file_size
├── is_deleted, created_at, deleted_at
└── Indexes: user_id, created_at, composite

audios table:
├── id (GUID, PK)
├── user_id (FK reference)
├── filename, file_path, file_size, duration_ms
├── is_deleted, created_at, deleted_at
└── Indexes: user_id, created_at, composite

user_quotas table:
├── user_id (GUID, PK)
├── video_count, total_size_bytes
├── audio_count, audio_total_size_bytes
├── last_updated
└── Index: last_updated
```

## 🔧 Common Operations

### View All Tables
```bash
psql -U postgres -d video_to_srt -c "\dt"
```

### View Specific Table Schema
```bash
psql -U postgres -d video_to_srt -c "\d videos"
```

### Query Data
```bash
psql -U postgres -d video_to_srt -c "SELECT COUNT(*) FROM videos;"
```

### Rollback (if needed)
```bash
# Rollback all migrations (in reverse order)
python migrations/migrate.py down

# Or rollback specific migration
python migrations/002_add_audio_quota_columns.py down
python migrations/001_initial_schema.py down
```

## 📝 Manual SQL Setup (Alternative)

Nếu prefer manual setup thay vì migrations:

```sql
-- Connect to database
psql -U postgres -d video_to_srt

-- Create videos table
CREATE TABLE videos (
    id VARCHAR(36) PRIMARY KEY UNIQUE NOT NULL,
    user_id VARCHAR(36) NOT NULL,
    filename VARCHAR(255) NOT NULL,
    file_path VARCHAR(500) NOT NULL UNIQUE,
    file_size INTEGER NOT NULL,
    is_deleted BOOLEAN DEFAULT false NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    deleted_at TIMESTAMP NULL
);

CREATE INDEX idx_video_user_id ON videos(user_id);
CREATE INDEX idx_video_user_id_created_at ON videos(user_id, created_at);
CREATE INDEX idx_video_user_id_is_deleted ON videos(user_id, is_deleted);

-- Create audios table
CREATE TABLE audios (
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

CREATE INDEX idx_audio_user_id ON audios(user_id);
CREATE INDEX idx_audio_user_id_created_at ON audios(user_id, created_at);
CREATE INDEX idx_audio_user_id_is_deleted ON audios(user_id, is_deleted);

-- Create user_quotas table
CREATE TABLE user_quotas (
    user_id VARCHAR(36) PRIMARY KEY UNIQUE NOT NULL,
    video_count INTEGER DEFAULT 0 NOT NULL,
    total_size_bytes INTEGER DEFAULT 0 NOT NULL,
    audio_count INTEGER DEFAULT 0 NOT NULL,
    audio_total_size_bytes INTEGER DEFAULT 0 NOT NULL,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX idx_user_quotas_last_updated ON user_quotas(last_updated);
```

## ⚠️ Troubleshooting

### Issue: "relation ... does not exist"
**Cause:** Database tables not created
**Fix:** Run migrations: `python migrations/migrate.py up`

### Issue: Migration fails with "already exists"
**Cause:** Table/column already exists from previous run
**Fix:** This is normal and idempotent (migrations handle this)

### Issue: Connection refused
**Cause:** PostgreSQL not running
**Fix:** 
```bash
# Windows
pg_ctl -D "C:\Program Files\PostgreSQL\16\data" start

# Or check if running
psql -U postgres -c "SELECT version();"
```

### Issue: "permission denied"
**Cause:** Wrong credentials
**Fix:** Check DATABASE_URL in config
```python
# Should be format:
DATABASE_URL = "postgresql://user:password@host:port/database"
```

## 📚 Related Documentation

For complete details, see:
- [DATABASE_SCHEMA.md](../DATABASE_SCHEMA.md) - Schema overview
- [DATABASE_DETAILED.md](../DATABASE_DETAILED.md) - Detailed schema documentation
- [DATABASE_SUMMARY.md](../DATABASE_SUMMARY.md) - Quick reference
- [MIGRATION_GUIDE.md](../MIGRATION_GUIDE.md) - How to create new migrations

## ✅ Checklist

After setup, verify:

- [ ] PostgreSQL is running
- [ ] Database `video_to_srt` is created
- [ ] DATABASE_URL is correctly configured
- [ ] Run migrations: `python migrations/migrate.py up`
- [ ] All 3 tables exist in database
- [ ] Indexes are created
- [ ] Can query data from tables

```bash
# Complete verification command
psql -U postgres -d video_to_srt << EOF
\dt
SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';
SELECT COUNT(*) FROM videos;
SELECT COUNT(*) FROM audios;
SELECT COUNT(*) FROM user_quotas;
EOF
```

## 🔄 Integration with Application

The app auto-initializes database on startup:

```python
# In app/main.py
from app.core.database import init_db

@app.on_event("startup")
async def startup():
    init_db()  # Creates tables if not exist
```

But **migrations should be run manually** for production deployments:

```bash
# Before deploying new version
python migrations/migrate.py up
```

This ensures schema changes are applied in correct order.
