"""
Y6 Practice Exam - Authentication Routes
Login, OTP, Logout endpoints
"""

from flask import Blueprint, request, jsonify, make_response, render_template, redirect, url_for
from datetime import datetime
import json
import sys
from pathlib import Path

# Add project paths
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src" / "core"))
sys.path.insert(0, str(PROJECT_ROOT / "dbs"))

from src.core.auth import (
    UserManager, PasswordManager, OTPManager, SessionManager,
    AuditLogger, login_required, get_client_ip
)
from dbs.connection import get_connection

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


@auth_bp.route('/login', methods=['GET'])
def login_page():
    """Render login page"""
    # Check if already logged in
    session_token = request.cookies.get('session_token')
    if session_token:
        session_data = SessionManager.validate_session(session_token)
        if session_data:
            # Redirect based on role
            if session_data['role_name'] == 'Admin':
                return redirect(url_for('admin.dashboard'))
            return redirect(url_for('student.dashboard'))

    return render_template('login.html')


@auth_bp.route('/login', methods=['POST'])
def login():
    """Step 1: Validate password"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'Invalid JSON data'}), 400

        email = data.get('email', '').strip().lower()
        password = data.get('password', '')

        if not email or not password:
            return jsonify({'error': 'Email and password are required'}), 400

        # Get user
        user = UserManager.get_user_by_email(email)

        if not user:
            return jsonify({'error': 'Invalid credentials'}), 401

        # Check if account is active
        if not user['is_active']:
            return jsonify({'error': 'Account is deactivated'}), 403

        # Check if account is locked
        is_locked, locked_until = UserManager.check_account_locked(user['id'])

        if is_locked:
            minutes_left = int((locked_until - datetime.now()).total_seconds() / 60)
            return jsonify({
                'error': f'Account locked. Try again in {minutes_left} minutes'
            }), 403

        # Verify password
        if not PasswordManager.verify_password(password, user['password_hash']):
            UserManager.record_failed_login(user['id'])
            AuditLogger.log_action(user['id'], 'login_failed', details={'reason': 'invalid_password'},
                                  ip_address=get_client_ip())
            return jsonify({'error': 'Invalid credentials'}), 401

        # Password correct - check for existing session
        session_token = request.cookies.get('session_token')

        if session_token:
            session_data = SessionManager.validate_session(session_token)
            if session_data and session_data['id'] == user['id']:
                # Already logged in, skip OTP
                UserManager.reset_failed_attempts(user['id'])

                # Update last login
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute("UPDATE users SET last_login = NOW() WHERE id = %s", (user['id'],))
                conn.commit()
                cursor.close()
                conn.close()

                AuditLogger.log_action(user['id'], 'login_trusted_device',
                                      details={'role': user['role_name']},
                                      ip_address=get_client_ip())

                return jsonify({
                    'success': True,
                    'skip_otp': True,
                    'message': 'Login successful',
                    'redirect': '/admin' if user['role_name'] == 'Admin' else '/student',
                    'user': {
                        'id': user['id'],
                        'email': user['email'],
                        'full_name': user['full_name'],
                        'role': user['role_name']
                    }
                }), 200

        # For simplicity in this Y6 system, we skip OTP and create session directly
        # (Parent/admin can login directly without email OTP)
        UserManager.reset_failed_attempts(user['id'])

        # Update last login
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET last_login = NOW() WHERE id = %s", (user['id'],))
        conn.commit()
        cursor.close()
        conn.close()

        # Create session
        session_token, expires_at = SessionManager.create_session(
            user['id'],
            get_client_ip(),
            request.user_agent.string if request.user_agent else None
        )

        AuditLogger.log_action(user['id'], 'login_success',
                              details={'role': user['role_name']},
                              ip_address=get_client_ip())

        # Create response with cookie
        response = make_response(jsonify({
            'success': True,
            'message': 'Login successful',
            'redirect': '/admin' if user['role_name'] == 'Admin' else '/student',
            'user': {
                'id': user['id'],
                'email': user['email'],
                'full_name': user['full_name'],
                'role': user['role_name']
            }
        }))

        # Set persistent HTTP-only cookie (30 days)
        response.set_cookie(
            'session_token',
            session_token,
            max_age=30*24*60*60,
            secure=False,  # Set to True in production with HTTPS
            httponly=True,
            samesite='Lax',
            path='/'
        )

        return response, 200

    except Exception as e:
        print(f"Login error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': 'Login failed'}), 500


@auth_bp.route('/logout', methods=['POST', 'GET'])
@login_required
def logout():
    """Logout and delete session"""
    try:
        session_token = request.cookies.get('session_token')

        if session_token:
            SessionManager.delete_session(session_token)

        AuditLogger.log_action(request.current_user['id'], 'logout',
                              ip_address=get_client_ip())

        # For GET requests (direct link), redirect to login
        if request.method == 'GET':
            response = make_response(redirect(url_for('auth.login_page')))
            response.delete_cookie('session_token', path='/', samesite='Lax')
            return response

        response = make_response(jsonify({'success': True, 'message': 'Logged out successfully'}))
        response.delete_cookie('session_token', path='/', samesite='Lax')

        return response, 200

    except Exception as e:
        print(f"Logout error: {e}")
        return jsonify({'error': 'Logout failed'}), 500


@auth_bp.route('/me', methods=['GET'])
@login_required
def get_current_user():
    """Get current user info"""
    try:
        user = request.current_user

        return jsonify({
            'user': {
                'id': user['id'],
                'email': user['email'],
                'full_name': user['full_name'],
                'role': user['role_name'],
                'permissions': json.loads(user['permissions']) if isinstance(user['permissions'], str) else user['permissions'],
                'last_login': user['last_login'].isoformat() if user['last_login'] else None
            }
        }), 200

    except Exception as e:
        print(f"Get user error: {e}")
        return jsonify({'error': 'Failed to get user info'}), 500


@auth_bp.route('/check-session', methods=['GET'])
def check_session():
    """Check if session is valid"""
    session_token = request.cookies.get('session_token')

    if not session_token:
        return jsonify({'authenticated': False}), 200

    session_data = SessionManager.validate_session(session_token)

    if not session_data:
        return jsonify({'authenticated': False}), 200

    return jsonify({
        'authenticated': True,
        'user': {
            'id': session_data['id'],
            'email': session_data['email'],
            'full_name': session_data['full_name'],
            'role': session_data['role_name']
        }
    }), 200


@auth_bp.route('/unauthorized')
def unauthorized():
    """Unauthorized access page"""
    return render_template('unauthorized.html'), 403


@auth_bp.route('/magic/<token>')
def magic_login(token):
    """Magic link authentication - auto-login and redirect to exam"""
    try:
        from src.core.email import MagicLinkManager

        # Validate magic link
        link_data = MagicLinkManager.validate_magic_link(token)

        if not link_data:
            return render_template('auth/magic_expired.html'), 400

        user_id = link_data['user_id']
        exam_id = link_data['exam_id']

        # Get user info
        user = UserManager.get_user_by_id(user_id)

        if not user or not user['is_active']:
            return render_template('auth/magic_expired.html'), 400

        # Create session
        session_token, expires_at = SessionManager.create_session(
            user_id,
            get_client_ip(),
            request.user_agent.string if request.user_agent else 'Magic Link'
        )

        # Log the action
        AuditLogger.log_action(user_id, 'magic_login',
                              resource_type='practice_exam', resource_id=str(exam_id),
                              details={'purpose': link_data['purpose']},
                              ip_address=get_client_ip())

        # Update last login
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET last_login = NOW() WHERE id = %s", (user_id,))
        conn.commit()
        cursor.close()
        conn.close()

        # Redirect to exam
        if link_data['purpose'] == 'exam_attempt':
            redirect_url = url_for('student.take_exam', exam_id=exam_id)
        else:
            redirect_url = url_for('student.dashboard')

        response = make_response(redirect(redirect_url))

        # Set session cookie
        response.set_cookie(
            'session_token',
            session_token,
            max_age=30*24*60*60,
            secure=False,
            httponly=True,
            samesite='Lax',
            path='/'
        )

        return response

    except Exception as e:
        print(f"Magic login error: {e}")
        import traceback
        traceback.print_exc()
        return render_template('auth/magic_expired.html'), 500


@auth_bp.route('/reset-password/<token>', methods=['GET'])
def reset_password_page(token):
    """Password reset page"""
    from src.core.email import MagicLinkManager

    # Check if token is valid (without consuming it)
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT ml.*, u.full_name, u.email
            FROM magic_links ml
            JOIN users u ON ml.user_id = u.id
            WHERE ml.token = %s AND ml.used_at IS NULL AND ml.expires_at > NOW()
            AND ml.purpose = 'password_reset'
        """, (token,))
        link = cursor.fetchone()

        if not link:
            return render_template('auth/magic_expired.html'), 400

        return render_template('auth/reset_password.html',
                             token=token,
                             user_name=link['full_name'],
                             user_email=link['email'])

    finally:
        cursor.close()
        conn.close()


@auth_bp.route('/reset-password/<token>', methods=['POST'])
def reset_password(token):
    """Process password reset"""
    from src.core.email import MagicLinkManager

    try:
        data = request.get_json()
        new_password = data.get('password', '')

        if len(new_password) < 6:
            return jsonify({'success': False, 'error': 'Password must be at least 6 characters'}), 400

        # Validate and consume token
        link_data = MagicLinkManager.validate_magic_link(token)

        if not link_data:
            return jsonify({'success': False, 'error': 'Invalid or expired reset link'}), 400

        if link_data['purpose'] != 'password_reset':
            return jsonify({'success': False, 'error': 'Invalid reset link'}), 400

        user_id = link_data['user_id']

        # Update password
        password_hash = PasswordManager.hash_password(new_password)

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET password_hash = %s WHERE id = %s", (password_hash, user_id))
        conn.commit()
        cursor.close()
        conn.close()

        AuditLogger.log_action(user_id, 'password_reset_completed',
                              ip_address=get_client_ip())

        return jsonify({'success': True, 'message': 'Password updated successfully'}), 200

    except Exception as e:
        print(f"Reset password error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
