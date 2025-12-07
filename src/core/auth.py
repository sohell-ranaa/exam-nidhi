"""
Y6 Practice Exam - Authentication System
RBAC with password + OTP, session management (adapted from ssh-guardian v3)
"""

import os
import sys
import secrets
import json
from pathlib import Path
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify, session, redirect, url_for
import bcrypt

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "dbs"))

from dbs.connection import get_connection
from config import SESSION_DURATION_DAYS, OTP_VALIDITY_MINUTES, MAX_FAILED_ATTEMPTS, LOCKOUT_DURATION_MINUTES


class AuthenticationError(Exception):
    """Base exception for authentication errors"""
    pass


class PasswordManager:
    """Password hashing and validation"""

    @staticmethod
    def hash_password(password):
        """Hash password using bcrypt"""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

    @staticmethod
    def verify_password(password, password_hash):
        """Verify password against hash"""
        return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))

    @staticmethod
    def validate_password_strength(password):
        """Validate password meets security requirements"""
        errors = []
        if len(password) < 8:
            errors.append("Password must be at least 8 characters long")
        return len(errors) == 0, errors


class OTPManager:
    """OTP generation and validation"""

    @staticmethod
    def generate_otp():
        """Generate 6-digit OTP"""
        return ''.join([str(secrets.randbelow(10)) for _ in range(6)])

    @staticmethod
    def create_otp(user_id, purpose='login', ip_address=None):
        """Create and store OTP"""
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            otp_code = OTPManager.generate_otp()
            expires_at = datetime.now() + timedelta(minutes=OTP_VALIDITY_MINUTES)

            cursor.execute("""
                INSERT INTO user_otps (user_id, otp_code, purpose, expires_at, ip_address)
                VALUES (%s, %s, %s, %s, %s)
            """, (user_id, otp_code, purpose, expires_at, ip_address))

            conn.commit()
            return otp_code

        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def verify_otp(user_id, otp_code, purpose='login'):
        """Verify OTP is valid and not expired"""
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            cursor.execute("""
                SELECT * FROM user_otps
                WHERE user_id = %s
                AND otp_code = %s
                AND purpose = %s
                AND expires_at > NOW()
                AND is_used = FALSE
                ORDER BY created_at DESC
                LIMIT 1
            """, (user_id, otp_code, purpose))

            otp = cursor.fetchone()

            if not otp:
                return False

            # Mark as used
            cursor.execute("""
                UPDATE user_otps
                SET is_used = TRUE, used_at = NOW()
                WHERE id = %s
            """, (otp['id'],))

            conn.commit()
            return True

        finally:
            cursor.close()
            conn.close()


class SessionManager:
    """Session management with secure cookies"""

    @staticmethod
    def generate_session_token():
        """Generate secure session token"""
        return secrets.token_urlsafe(32)

    @staticmethod
    def create_session(user_id, ip_address=None, user_agent=None):
        """Create new session"""
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            session_token = SessionManager.generate_session_token()
            expires_at = datetime.now() + timedelta(days=SESSION_DURATION_DAYS)

            cursor.execute("""
                INSERT INTO user_sessions (user_id, session_token, ip_address, user_agent, expires_at)
                VALUES (%s, %s, %s, %s, %s)
            """, (user_id, session_token, ip_address, user_agent, expires_at))

            conn.commit()

            return session_token, expires_at

        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def validate_session(session_token):
        """Validate session token and return user"""
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            cursor.execute("""
                SELECT s.*, u.*, r.name as role_name, r.permissions
                FROM user_sessions s
                JOIN users u ON s.user_id = u.id
                JOIN roles r ON u.role_id = r.id
                WHERE s.session_token = %s
                AND s.expires_at > NOW()
                AND u.is_active = TRUE
            """, (session_token,))

            session_data = cursor.fetchone()

            if session_data:
                # Update last activity
                cursor.execute("""
                    UPDATE user_sessions
                    SET last_activity = NOW()
                    WHERE session_token = %s
                """, (session_token,))
                conn.commit()

            return session_data

        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def delete_session(session_token):
        """Delete session (logout)"""
        conn = get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                DELETE FROM user_sessions
                WHERE session_token = %s
            """, (session_token,))

            conn.commit()

        finally:
            cursor.close()
            conn.close()


class UserManager:
    """User management operations"""

    @staticmethod
    def get_user_by_email(email):
        """Get user by email"""
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            cursor.execute("""
                SELECT u.*, r.name as role_name, r.permissions
                FROM users u
                JOIN roles r ON u.role_id = r.id
                WHERE u.email = %s
            """, (email,))

            return cursor.fetchone()

        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def get_user_by_id(user_id):
        """Get user by ID"""
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            cursor.execute("""
                SELECT u.*, r.name as role_name, r.permissions
                FROM users u
                JOIN roles r ON u.role_id = r.id
                WHERE u.id = %s
            """, (user_id,))

            return cursor.fetchone()

        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def check_account_locked(user_id):
        """Check if account is locked"""
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            cursor.execute("""
                SELECT locked_until FROM users
                WHERE id = %s
            """, (user_id,))

            result = cursor.fetchone()

            if result and result['locked_until']:
                if result['locked_until'] > datetime.now():
                    return True, result['locked_until']
                else:
                    # Unlock account
                    cursor.execute("""
                        UPDATE users
                        SET locked_until = NULL, failed_login_attempts = 0
                        WHERE id = %s
                    """, (user_id,))
                    conn.commit()

            return False, None

        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def record_failed_login(user_id):
        """Record failed login attempt"""
        conn = get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                UPDATE users
                SET failed_login_attempts = failed_login_attempts + 1
                WHERE id = %s
            """, (user_id,))

            # Check if should lock
            cursor.execute("""
                SELECT failed_login_attempts FROM users WHERE id = %s
            """, (user_id,))

            result = cursor.fetchone()

            if result and result[0] >= MAX_FAILED_ATTEMPTS:
                locked_until = datetime.now() + timedelta(minutes=LOCKOUT_DURATION_MINUTES)
                cursor.execute("""
                    UPDATE users
                    SET locked_until = %s
                    WHERE id = %s
                """, (locked_until, user_id))

            conn.commit()

        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def reset_failed_attempts(user_id):
        """Reset failed login attempts"""
        conn = get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                UPDATE users
                SET failed_login_attempts = 0, locked_until = NULL
                WHERE id = %s
            """, (user_id,))

            conn.commit()

        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def create_user(email, password, full_name, role_id=2, created_by=None):
        """Create a new user"""
        conn = get_connection()
        cursor = conn.cursor()

        try:
            password_hash = PasswordManager.hash_password(password)

            cursor.execute("""
                INSERT INTO users (email, password_hash, full_name, role_id, created_by, is_active)
                VALUES (%s, %s, %s, %s, %s, TRUE)
            """, (email.lower().strip(), password_hash, full_name, role_id, created_by))

            conn.commit()
            return cursor.lastrowid

        finally:
            cursor.close()
            conn.close()


class AuditLogger:
    """Audit logging for security actions"""

    @staticmethod
    def log_action(user_id, action, resource_type=None, resource_id=None, details=None,
                   ip_address=None, user_agent=None):
        """Log user action"""
        conn = get_connection()
        cursor = conn.cursor()

        try:
            details_json = json.dumps(details) if details else None

            cursor.execute("""
                INSERT INTO audit_logs (user_id, action, resource_type, resource_id,
                                       details, ip_address, user_agent)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (user_id, action, resource_type, resource_id, details_json,
                  ip_address, user_agent))

            conn.commit()

        finally:
            cursor.close()
            conn.close()


# Authentication decorators
def _is_api_request():
    """Check if request is an API call or browser request"""
    accept = request.headers.get('Accept', '')
    if 'application/json' in accept and 'text/html' not in accept:
        return True
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return True
    if request.path.startswith('/api/'):
        return True
    return False


def login_required(f):
    """Decorator to require authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        session_token = request.cookies.get('session_token')

        if not session_token:
            if _is_api_request():
                return jsonify({'error': 'Authentication required', 'code': 'AUTH_REQUIRED'}), 401
            return redirect(url_for('auth.login_page'))

        session_data = SessionManager.validate_session(session_token)

        if not session_data:
            if _is_api_request():
                return jsonify({'error': 'Invalid or expired session', 'code': 'INVALID_SESSION'}), 401
            return redirect(url_for('auth.login_page'))

        # Add user data to request context
        request.current_user = session_data

        return f(*args, **kwargs)

    return decorated_function


def role_required(*role_names):
    """Decorator to require specific role"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            session_token = request.cookies.get('session_token')

            if not session_token:
                if _is_api_request():
                    return jsonify({'error': 'Authentication required'}), 401
                return redirect(url_for('auth.login_page'))

            session_data = SessionManager.validate_session(session_token)

            if not session_data:
                if _is_api_request():
                    return jsonify({'error': 'Invalid session'}), 401
                return redirect(url_for('auth.login_page'))

            # Check role
            if session_data['role_name'] not in role_names:
                if _is_api_request():
                    return jsonify({'error': 'Insufficient permissions'}), 403
                return redirect(url_for('auth.unauthorized'))

            request.current_user = session_data

            return f(*args, **kwargs)

        return decorated_function

    return decorator


def permission_required(permission_name):
    """Decorator to require specific permission"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            session_token = request.cookies.get('session_token')

            if not session_token:
                if _is_api_request():
                    return jsonify({'error': 'Authentication required'}), 401
                return redirect(url_for('auth.login_page'))

            session_data = SessionManager.validate_session(session_token)

            if not session_data:
                if _is_api_request():
                    return jsonify({'error': 'Invalid session'}), 401
                return redirect(url_for('auth.login_page'))

            # Check permission
            permissions = json.loads(session_data['permissions']) if isinstance(session_data['permissions'], str) else session_data['permissions']

            if not permissions.get(permission_name, False):
                if _is_api_request():
                    return jsonify({'error': 'Insufficient permissions'}), 403
                return redirect(url_for('auth.unauthorized'))

            request.current_user = session_data

            return f(*args, **kwargs)

        return decorated_function

    return decorator
