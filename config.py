"""
Y6 Practice Exam System - Configuration
Spring Gate Private School, Malaysia
"""

import os

# Set timezone to Malaysia (GMT+8)
os.environ['TZ'] = 'Asia/Kuala_Lumpur'
try:
    import time
    time.tzset()
except:
    pass

# Flask Configuration
SECRET_KEY = os.getenv('SECRET_KEY', 'y6-practice-exam-secret-key-2024')
DEBUG = os.getenv('DEBUG', 'True').lower() == 'true'

# Database Configuration (same as ssh-guardian v3)
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", 3306)),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", "123123"),
    "database": os.getenv("DB_NAME", "y6_practice_exam"),
    "charset": "utf8mb4",
    "collation": "utf8mb4_unicode_ci",
    "autocommit": False,
    "use_pure": False,
    "init_command": "SET time_zone = '+08:00'"  # Malaysia timezone (GMT+8)
}

# Connection Pool Configuration
POOL_CONFIG = {
    "pool_name": "y6_exam_pool",
    "pool_size": int(os.getenv("DB_POOL_SIZE", 10)),
    "pool_reset_session": True,
    "connect_timeout": int(os.getenv("DB_TIMEOUT", 10))
}

# Redis Configuration
REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
REDIS_DB = int(os.getenv('REDIS_DB', 1))  # Different DB than ssh-guardian
REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', None)

# Session Configuration
SESSION_DURATION_DAYS = 30
OTP_VALIDITY_MINUTES = 5
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_DURATION_MINUTES = 30

# Application Settings
APP_NAME = "Y6 Practice Exam"
SCHOOL_NAME = "Spring Gate Private School"
SCHOOL_LOCATION = "Selangor, Malaysia"

# Subjects
SUBJECTS = ['English', 'Mathematics', 'ICT', 'Science']
