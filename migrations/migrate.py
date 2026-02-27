"""
Migration runner script
Executes all migrations in order or rollback
"""

import sys
import os
import importlib.util
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def load_migration(migration_path):
    """Load a migration module dynamically"""
    spec = importlib.util.spec_from_file_location("migration", migration_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def get_migrations():
    """Get all migration files sorted by name (version)"""
    migrations_dir = Path(__file__).parent
    migration_files = sorted([
        f for f in migrations_dir.glob("*.py")
        if f.name.startswith(('00', '01', '02', '03', '04', '05', '06', '07', '08', '09')) and f.name.endswith('.py')
    ])
    return migration_files


def migrate_up():
    """Run all pending migrations"""
    print("=" * 60)
    print("RUNNING MIGRATIONS (UP)")
    print("=" * 60)
    
    migrations = get_migrations()
    if not migrations:
        print("No migrations found")
        return
    
    for migration_file in migrations:
        print(f"\n📌 Running: {migration_file.name}")
        print("-" * 60)
        try:
            module = load_migration(migration_file)
            module.migrate_up()
            print(f"✅ {migration_file.name} completed\n")
        except Exception as e:
            print(f"❌ {migration_file.name} failed: {e}\n")
            raise


def migrate_down():
    """Rollback all migrations in reverse order"""
    print("=" * 60)
    print("ROLLING BACK MIGRATIONS (DOWN)")
    print("=" * 60)
    
    migrations = get_migrations()
    if not migrations:
        print("No migrations found")
        return
    
    # Reverse order for rollback
    for migration_file in reversed(migrations):
        print(f"\n📌 Rolling back: {migration_file.name}")
        print("-" * 60)
        try:
            module = load_migration(migration_file)
            module.migrate_down()
            print(f"✅ {migration_file.name} rolled back\n")
        except Exception as e:
            print(f"❌ {migration_file.name} rollback failed: {e}\n")
            raise


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Migration runner for database schema")
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
    
    print("=" * 60)
    print("✓ All migrations completed!")
    print("=" * 60)
