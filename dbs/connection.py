"""
Y6 Practice Exam - Database Connection Module
Centralized database connection with pooling (adapted from ssh-guardian v3)
"""

import mysql.connector
from mysql.connector import pooling, Error
from typing import Optional, Tuple
import os
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config import DB_CONFIG, POOL_CONFIG

# Global connection pool
connection_pool = None


def initialize_pool():
    """Initialize the connection pool"""
    global connection_pool

    try:
        connection_pool = pooling.MySQLConnectionPool(
            **POOL_CONFIG,
            **DB_CONFIG
        )
        print(f"Database connection pool '{POOL_CONFIG['pool_name']}' created successfully")
        print(f"   Pool size: {POOL_CONFIG['pool_size']} connections")
        print(f"   Database: {DB_CONFIG['database']}")
        return True
    except Error as e:
        print(f"Error creating connection pool: {e}")
        connection_pool = None
        return False


def get_connection():
    """
    Get a connection from the pool.

    Returns:
        mysql.connector connection object

    Raises:
        Error: If connection cannot be established
    """
    global connection_pool

    try:
        if connection_pool is None:
            initialize_pool()

        if connection_pool:
            conn = connection_pool.get_connection()
            return conn
        else:
            # Fallback to direct connection if pool initialization failed
            print("Connection pool not available, using direct connection")
            return mysql.connector.connect(**DB_CONFIG)

    except Error as e:
        print(f"Error getting connection: {e}")
        raise


def test_connection():
    """
    Test database connection and display information.

    Returns:
        bool: True if connection successful, False otherwise
    """
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        # Test basic connection
        cursor.execute("SELECT VERSION() as version, DATABASE() as db_name, USER() as user")
        result = cursor.fetchone()

        print("=" * 60)
        print("Y6 PRACTICE EXAM - DATABASE CONNECTION TEST")
        print("=" * 60)
        print(f"MySQL Version:    {result['version']}")
        print(f"Database:         {result['db_name']}")
        print(f"User:             {result['user']}")
        print(f"Host:             {DB_CONFIG['host']}:{DB_CONFIG['port']}")
        print(f"Pool Size:        {POOL_CONFIG['pool_size']} connections")
        print("=" * 60)
        print("Connection successful!")

        cursor.close()
        conn.close()

        return True

    except Error as e:
        print("=" * 60)
        print("DATABASE CONNECTION FAILED")
        print("=" * 60)
        print(f"Error: {e}")
        print(f"\nConfiguration:")
        print(f"  Host: {DB_CONFIG['host']}")
        print(f"  Port: {DB_CONFIG['port']}")
        print(f"  Database: {DB_CONFIG['database']}")
        print(f"  User: {DB_CONFIG['user']}")
        print("=" * 60)
        return False


def execute_query(query: str, params: Optional[Tuple] = None, fetch_one=False, fetch_all=False):
    """
    Execute a query and return results.

    Args:
        query: SQL query to execute
        params: Query parameters (optional)
        fetch_one: If True, return single row
        fetch_all: If True, return all rows

    Returns:
        Result set or None
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute(query, params or ())

        if fetch_one:
            result = cursor.fetchone()
        elif fetch_all:
            result = cursor.fetchall()
        else:
            result = None

        conn.commit()
        return result

    except Error as e:
        conn.rollback()
        print(f"Query execution error: {e}")
        raise
    finally:
        cursor.close()
        conn.close()


# Initialize pool on module import
initialize_pool()


if __name__ == "__main__":
    """Run connection test when executed directly"""
    print("\nTesting Y6 Practice Exam Database Connection...\n")
    test_connection()
