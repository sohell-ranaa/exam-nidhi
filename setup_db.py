"""
Y6 Practice Exam - Database Setup Script
Creates the database and runs the schema
"""

import mysql.connector
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from config import DB_CONFIG

def setup_database():
    """Create database and run schema"""
    print("="*60)
    print("Y6 PRACTICE EXAM - DATABASE SETUP")
    print("="*60)

    # Connect without database first
    conn_config = {
        'host': DB_CONFIG['host'],
        'port': DB_CONFIG['port'],
        'user': DB_CONFIG['user'],
        'password': DB_CONFIG['password']
    }

    try:
        print(f"\nConnecting to MySQL at {DB_CONFIG['host']}:{DB_CONFIG['port']}...")
        conn = mysql.connector.connect(**conn_config)
        cursor = conn.cursor()

        # Create database
        print(f"Creating database '{DB_CONFIG['database']}'...")
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_CONFIG['database']} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        cursor.execute(f"USE {DB_CONFIG['database']}")

        # Read and execute schema
        schema_path = PROJECT_ROOT / "dbs" / "migrations" / "001_schema.sql"
        print(f"Running schema from {schema_path}...")

        with open(schema_path, 'r') as f:
            schema = f.read()

        # Split by statement and execute
        statements = schema.split(';')
        for stmt in statements:
            stmt = stmt.strip()
            if stmt and not stmt.startswith('--') and not stmt.startswith('CREATE DATABASE') and not stmt.startswith('USE '):
                try:
                    cursor.execute(stmt)
                except mysql.connector.Error as e:
                    if 'already exists' in str(e) or 'Duplicate' in str(e):
                        pass  # Ignore duplicate errors
                    else:
                        print(f"  Warning: {e}")

        conn.commit()
        print("\nDatabase setup complete!")

        # Show table counts
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()
        print(f"\nCreated {len(tables)} tables:")
        for table in tables:
            print(f"  - {table[0]}")

        cursor.close()
        conn.close()

        return True

    except mysql.connector.Error as e:
        print(f"\nError: {e}")
        print("\nMake sure MySQL is running and credentials are correct in config.py")
        return False


if __name__ == "__main__":
    if setup_database():
        print("\n" + "="*60)
        print("Next steps:")
        print("  1. Run: python seeds/seed_questions.py")
        print("  2. Run: python app.py")
        print("  3. Access: http://localhost:5001")
        print("="*60)
