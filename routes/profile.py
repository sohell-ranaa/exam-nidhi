"""
Y6 Practice Exam - User Profile Routes
Profile management, password change, settings
"""

from flask import Blueprint, request, jsonify, render_template, redirect, url_for
from datetime import datetime
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src" / "core"))
sys.path.insert(0, str(PROJECT_ROOT / "dbs"))

from src.core.auth import login_required, PasswordManager, AuditLogger, get_client_ip
from dbs.connection import get_connection

profile_bp = Blueprint('profile', __name__, url_prefix='/profile')


@profile_bp.route('/')
@login_required
def view_profile():
    """View user profile"""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    user_id = request.current_user['id']

    try:
        # Get user details
        cursor.execute("""
            SELECT u.*, r.name as role_name
            FROM users u
            JOIN roles r ON u.role_id = r.id
            WHERE u.id = %s
        """, (user_id,))
        user = cursor.fetchone()

        # Get activity stats
        cursor.execute("""
            SELECT
                (SELECT COUNT(*) FROM user_sessions WHERE user_id = %s) as total_sessions,
                (SELECT MAX(created_at) FROM user_sessions WHERE user_id = %s) as last_activity
        """, (user_id, user_id))
        activity = cursor.fetchone()

        # Get recent audit logs
        cursor.execute("""
            SELECT action, resource_type, details, ip_address, created_at
            FROM audit_logs
            WHERE user_id = %s
            ORDER BY created_at DESC
            LIMIT 10
        """, (user_id,))
        recent_activity = cursor.fetchall()

        for act in recent_activity:
            if act['created_at']:
                act['created_at'] = act['created_at'].strftime('%d %b %Y %H:%M')
            if act['details'] and isinstance(act['details'], str):
                try:
                    act['details'] = json.loads(act['details'])
                except:
                    pass

        # Format dates
        if user['created_at']:
            user['created_at'] = user['created_at'].strftime('%d %b %Y')
        if user['last_login']:
            user['last_login'] = user['last_login'].strftime('%d %b %Y %H:%M')

        return render_template('profile/view.html',
                             profile=user,
                             activity=activity,
                             recent_activity=recent_activity,
                             user=request.current_user)

    finally:
        cursor.close()
        conn.close()


@profile_bp.route('/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    """Edit user profile"""
    user_id = request.current_user['id']

    if request.method == 'POST':
        try:
            data = request.get_json()
            full_name = data.get('full_name', '').strip()

            if not full_name:
                return jsonify({'success': False, 'error': 'Name is required'}), 400

            if len(full_name) < 2 or len(full_name) > 100:
                return jsonify({'success': False, 'error': 'Name must be 2-100 characters'}), 400

            conn = get_connection()
            cursor = conn.cursor()

            try:
                cursor.execute("""
                    UPDATE users SET full_name = %s, updated_at = NOW()
                    WHERE id = %s
                """, (full_name, user_id))
                conn.commit()

                AuditLogger.log_action(user_id, 'profile_updated',
                                      resource_type='user', resource_id=str(user_id),
                                      details={'full_name': full_name},
                                      ip_address=get_client_ip())

                return jsonify({'success': True, 'message': 'Profile updated successfully'}), 200

            finally:
                cursor.close()
                conn.close()

        except Exception as e:
            print(f"Edit profile error: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    return render_template('profile/edit.html', user=request.current_user)


@profile_bp.route('/password', methods=['GET', 'POST'])
@login_required
def change_password():
    """Change user password"""
    user_id = request.current_user['id']

    if request.method == 'POST':
        try:
            data = request.get_json()
            current_password = data.get('current_password', '')
            new_password = data.get('new_password', '')
            confirm_password = data.get('confirm_password', '')

            # Validate
            if not current_password or not new_password or not confirm_password:
                return jsonify({'success': False, 'error': 'All fields are required'}), 400

            if new_password != confirm_password:
                return jsonify({'success': False, 'error': 'New passwords do not match'}), 400

            if len(new_password) < 6:
                return jsonify({'success': False, 'error': 'Password must be at least 6 characters'}), 400

            if new_password == current_password:
                return jsonify({'success': False, 'error': 'New password must be different'}), 400

            conn = get_connection()
            cursor = conn.cursor(dictionary=True)

            try:
                # Verify current password
                cursor.execute("SELECT password_hash FROM users WHERE id = %s", (user_id,))
                user = cursor.fetchone()

                if not user or not PasswordManager.verify_password(current_password, user['password_hash']):
                    return jsonify({'success': False, 'error': 'Current password is incorrect'}), 400

                # Update password
                new_hash = PasswordManager.hash_password(new_password)
                cursor.execute("""
                    UPDATE users SET password_hash = %s, password_changed_at = NOW(), updated_at = NOW()
                    WHERE id = %s
                """, (new_hash, user_id))
                conn.commit()

                AuditLogger.log_action(user_id, 'password_changed',
                                      resource_type='user', resource_id=str(user_id),
                                      ip_address=get_client_ip())

                return jsonify({'success': True, 'message': 'Password changed successfully'}), 200

            finally:
                cursor.close()
                conn.close()

        except Exception as e:
            print(f"Change password error: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    return render_template('profile/password.html', user=request.current_user)


@profile_bp.route('/sessions')
@login_required
def view_sessions():
    """View active sessions"""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    user_id = request.current_user['id']

    try:
        cursor.execute("""
            SELECT id, ip_address, user_agent, created_at, expires_at,
                   CASE WHEN token = %s THEN TRUE ELSE FALSE END as is_current
            FROM user_sessions
            WHERE user_id = %s AND expires_at > NOW()
            ORDER BY created_at DESC
        """, (request.cookies.get('session_token', ''), user_id))
        sessions = cursor.fetchall()

        for sess in sessions:
            if sess['created_at']:
                sess['created_at'] = sess['created_at'].strftime('%d %b %Y %H:%M')
            if sess['expires_at']:
                sess['expires_at'] = sess['expires_at'].strftime('%d %b %Y %H:%M')

        return render_template('profile/sessions.html',
                             sessions=sessions,
                             user=request.current_user)

    finally:
        cursor.close()
        conn.close()


@profile_bp.route('/sessions/<int:session_id>/revoke', methods=['POST'])
@login_required
def revoke_session(session_id):
    """Revoke a specific session"""
    try:
        user_id = request.current_user['id']

        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            # Verify session belongs to user
            cursor.execute("""
                SELECT token FROM user_sessions WHERE id = %s AND user_id = %s
            """, (session_id, user_id))
            session = cursor.fetchone()

            if not session:
                return jsonify({'success': False, 'error': 'Session not found'}), 404

            # Don't allow revoking current session
            current_token = request.cookies.get('session_token', '')
            if session['token'] == current_token:
                return jsonify({'success': False, 'error': 'Cannot revoke current session'}), 400

            # Delete session
            cursor.execute("DELETE FROM user_sessions WHERE id = %s", (session_id,))
            conn.commit()

            AuditLogger.log_action(user_id, 'session_revoked',
                                  resource_type='session', resource_id=str(session_id),
                                  ip_address=get_client_ip())

            return jsonify({'success': True, 'message': 'Session revoked'}), 200

        finally:
            cursor.close()
            conn.close()

    except Exception as e:
        print(f"Revoke session error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@profile_bp.route('/sessions/revoke-all', methods=['POST'])
@login_required
def revoke_all_sessions():
    """Revoke all sessions except current"""
    try:
        user_id = request.current_user['id']
        current_token = request.cookies.get('session_token', '')

        conn = get_connection()
        cursor = conn.cursor()

        try:
            # Delete all sessions except current
            cursor.execute("""
                DELETE FROM user_sessions
                WHERE user_id = %s AND token != %s
            """, (user_id, current_token))
            deleted = cursor.rowcount
            conn.commit()

            AuditLogger.log_action(user_id, 'all_sessions_revoked',
                                  resource_type='user', resource_id=str(user_id),
                                  details={'deleted_count': deleted},
                                  ip_address=get_client_ip())

            return jsonify({
                'success': True,
                'message': f'Revoked {deleted} session(s)',
                'count': deleted
            }), 200

        finally:
            cursor.close()
            conn.close()

    except Exception as e:
        print(f"Revoke all sessions error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
