"""
Y6 Practice Exam - Settings Routes
System settings, SMTP configuration, marking thresholds
"""

from flask import Blueprint, request, jsonify, render_template
from datetime import datetime
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src" / "core"))
sys.path.insert(0, str(PROJECT_ROOT / "dbs"))

from src.core.auth import role_required, AuditLogger, get_client_ip
from src.core.email import EmailSettings, EmailService
from src.core.cache import get_cache
from dbs.connection import get_connection

settings_bp = Blueprint('settings', __name__, url_prefix='/settings')


class SystemSettings:
    """Manage all system settings"""

    @classmethod
    def get_all_settings(cls) -> dict:
        """Get all system settings"""
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            cursor.execute("SELECT setting_key, setting_value FROM system_settings")
            rows = cursor.fetchall()

            settings = {}
            for row in rows:
                try:
                    settings[row['setting_key']] = json.loads(row['setting_value'])
                except:
                    settings[row['setting_key']] = row['setting_value']

            # Set defaults if not present
            defaults = cls.get_defaults()
            for key, value in defaults.items():
                if key not in settings:
                    settings[key] = value

            return settings

        finally:
            cursor.close()
            conn.close()

    @classmethod
    def get_setting(cls, key: str, default=None):
        """Get a specific setting"""
        cache = get_cache()
        cache_key = f"settings:{key}"

        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            cursor.execute("SELECT setting_value FROM system_settings WHERE setting_key = %s", (key,))
            row = cursor.fetchone()

            if row and row['setting_value']:
                try:
                    value = json.loads(row['setting_value'])
                except:
                    value = row['setting_value']
            else:
                value = default

            cache.set(cache_key, value, 3600)
            return value

        finally:
            cursor.close()
            conn.close()

    @classmethod
    def save_setting(cls, key: str, value) -> bool:
        """Save a setting"""
        conn = get_connection()
        cursor = conn.cursor()

        try:
            value_json = json.dumps(value) if not isinstance(value, str) else value

            cursor.execute("""
                INSERT INTO system_settings (setting_key, setting_value, updated_at)
                VALUES (%s, %s, NOW())
                ON DUPLICATE KEY UPDATE setting_value = %s, updated_at = NOW()
            """, (key, value_json, value_json))

            conn.commit()

            # Clear cache
            cache = get_cache()
            cache.delete(f"settings:{key}")

            return True

        except Exception as e:
            print(f"Save setting error: {e}")
            return False

        finally:
            cursor.close()
            conn.close()

    @classmethod
    def get_defaults(cls) -> dict:
        """Get default settings"""
        return {
            'marking_thresholds': {
                'excellent': 80,
                'good': 60,
                'satisfactory': 40,
                'needs_improvement': 0
            },
            'grade_labels': {
                'excellent': 'A',
                'good': 'B',
                'satisfactory': 'C',
                'needs_improvement': 'D'
            },
            'exam_defaults': {
                'duration_minutes': 60,
                'allow_late_submission': False,
                'show_correct_answers': True,
                'show_marks_per_question': True,
                'randomize_questions': False
            },
            'notifications': {
                'email_on_assignment': True,
                'email_on_results': True,
                'email_deadline_reminder': True,
                'reminder_hours_before': 24
            },
            'display': {
                'items_per_page': 20,
                'date_format': '%d %b %Y',
                'time_format': '%H:%M',
                'show_leaderboard': True
            },
            'system': {
                'timezone': 'Asia/Kuala_Lumpur',
                'school_name': 'Spring Gate Private School',
                'school_country': 'Malaysia'
            }
        }


@settings_bp.route('/')
@role_required('Admin')
def settings_page():
    """Settings dashboard"""
    all_settings = SystemSettings.get_all_settings()
    smtp_settings = EmailSettings.get_settings()

    return render_template('admin/settings.html',
                         settings=all_settings,
                         smtp=smtp_settings,
                         user=request.current_user)


@settings_bp.route('/smtp', methods=['GET', 'POST'])
@role_required('Admin')
def smtp_settings():
    """SMTP settings page"""
    if request.method == 'POST':
        try:
            data = request.get_json()

            smtp_config = {
                'smtp_host': data.get('smtp_host', '').strip(),
                'smtp_port': int(data.get('smtp_port', 587)),
                'smtp_user': data.get('smtp_user', '').strip(),
                'smtp_password': data.get('smtp_password', ''),
                'smtp_from_email': data.get('smtp_from_email', '').strip(),
                'smtp_from_name': data.get('smtp_from_name', 'Y6 Practice Exam').strip(),
                'smtp_use_tls': data.get('smtp_use_tls', True),
                'smtp_enabled': data.get('smtp_enabled', False)
            }

            EmailSettings.save_settings(smtp_config)

            AuditLogger.log_action(request.current_user['id'], 'smtp_settings_updated',
                                  resource_type='settings',
                                  ip_address=get_client_ip())

            return jsonify({'success': True, 'message': 'SMTP settings saved'}), 200

        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    smtp = EmailSettings.get_settings()
    return render_template('admin/settings_smtp.html', smtp=smtp, user=request.current_user)


@settings_bp.route('/smtp/test', methods=['POST'])
@role_required('Admin')
def test_smtp():
    """Test SMTP connection"""
    try:
        data = request.get_json()

        smtp_config = {
            'smtp_host': data.get('smtp_host', '').strip(),
            'smtp_port': int(data.get('smtp_port', 587)),
            'smtp_user': data.get('smtp_user', '').strip(),
            'smtp_password': data.get('smtp_password', ''),
            'smtp_use_tls': data.get('smtp_use_tls', True)
        }

        success, message = EmailSettings.test_connection(smtp_config)

        return jsonify({'success': success, 'message': message}), 200

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@settings_bp.route('/smtp/send-test', methods=['POST'])
@role_required('Admin')
def send_test_email():
    """Send a test email to verify SMTP is working end-to-end"""
    try:
        data = request.get_json()
        to_email = data.get('to_email', '').strip()

        if not to_email:
            return jsonify({'success': False, 'error': 'Email address is required'}), 400

        success, message = EmailService.send_test_email(to_email)

        if success:
            AuditLogger.log_action(request.current_user['id'], 'test_email_sent',
                                  resource_type='settings',
                                  details={'to_email': to_email},
                                  ip_address=get_client_ip())

        return jsonify({'success': success, 'message': message}), 200

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@settings_bp.route('/marking', methods=['GET', 'POST'])
@role_required('Admin')
def marking_settings():
    """Marking threshold settings"""
    if request.method == 'POST':
        try:
            data = request.get_json()

            thresholds = {
                'excellent': int(data.get('excellent', 80)),
                'good': int(data.get('good', 60)),
                'satisfactory': int(data.get('satisfactory', 40)),
                'needs_improvement': 0
            }

            labels = {
                'excellent': data.get('label_excellent', 'A'),
                'good': data.get('label_good', 'B'),
                'satisfactory': data.get('label_satisfactory', 'C'),
                'needs_improvement': data.get('label_needs_improvement', 'D')
            }

            SystemSettings.save_setting('marking_thresholds', thresholds)
            SystemSettings.save_setting('grade_labels', labels)

            AuditLogger.log_action(request.current_user['id'], 'marking_settings_updated',
                                  resource_type='settings',
                                  details={'thresholds': thresholds, 'labels': labels},
                                  ip_address=get_client_ip())

            return jsonify({'success': True, 'message': 'Marking settings saved'}), 200

        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    thresholds = SystemSettings.get_setting('marking_thresholds', SystemSettings.get_defaults()['marking_thresholds'])
    labels = SystemSettings.get_setting('grade_labels', SystemSettings.get_defaults()['grade_labels'])

    return render_template('admin/settings_marking.html',
                         thresholds=thresholds,
                         labels=labels,
                         user=request.current_user)


@settings_bp.route('/exam', methods=['GET', 'POST'])
@role_required('Admin')
def exam_settings():
    """Exam default settings"""
    if request.method == 'POST':
        try:
            data = request.get_json()

            exam_defaults = {
                'duration_minutes': int(data.get('duration_minutes', 60)),
                'allow_late_submission': data.get('allow_late_submission', False),
                'show_correct_answers': data.get('show_correct_answers', True),
                'show_marks_per_question': data.get('show_marks_per_question', True),
                'randomize_questions': data.get('randomize_questions', False)
            }

            SystemSettings.save_setting('exam_defaults', exam_defaults)

            AuditLogger.log_action(request.current_user['id'], 'exam_settings_updated',
                                  resource_type='settings',
                                  ip_address=get_client_ip())

            return jsonify({'success': True, 'message': 'Exam settings saved'}), 200

        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    exam_defaults = SystemSettings.get_setting('exam_defaults', SystemSettings.get_defaults()['exam_defaults'])
    return render_template('admin/settings_exam.html', exam_defaults=exam_defaults, user=request.current_user)


@settings_bp.route('/notifications', methods=['GET', 'POST'])
@role_required('Admin')
def notification_settings():
    """Notification settings"""
    if request.method == 'POST':
        try:
            data = request.get_json()

            notifications = {
                'email_on_assignment': data.get('email_on_assignment', True),
                'email_on_results': data.get('email_on_results', True),
                'email_deadline_reminder': data.get('email_deadline_reminder', True),
                'reminder_hours_before': int(data.get('reminder_hours_before', 24))
            }

            SystemSettings.save_setting('notifications', notifications)

            AuditLogger.log_action(request.current_user['id'], 'notification_settings_updated',
                                  resource_type='settings',
                                  ip_address=get_client_ip())

            return jsonify({'success': True, 'message': 'Notification settings saved'}), 200

        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    notifications = SystemSettings.get_setting('notifications', SystemSettings.get_defaults()['notifications'])
    return render_template('admin/settings_notifications.html', notifications=notifications, user=request.current_user)


@settings_bp.route('/display', methods=['GET', 'POST'])
@role_required('Admin')
def display_settings():
    """Display settings"""
    if request.method == 'POST':
        try:
            data = request.get_json()

            display = {
                'items_per_page': int(data.get('items_per_page', 20)),
                'date_format': data.get('date_format', '%d %b %Y'),
                'time_format': data.get('time_format', '%H:%M'),
                'show_leaderboard': data.get('show_leaderboard', True)
            }

            SystemSettings.save_setting('display', display)

            AuditLogger.log_action(request.current_user['id'], 'display_settings_updated',
                                  resource_type='settings',
                                  ip_address=get_client_ip())

            return jsonify({'success': True, 'message': 'Display settings saved'}), 200

        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    display = SystemSettings.get_setting('display', SystemSettings.get_defaults()['display'])
    return render_template('admin/settings_display.html', display=display, user=request.current_user)


@settings_bp.route('/system', methods=['GET', 'POST'])
@role_required('Admin')
def system_settings():
    """System settings (timezone, school info)"""
    if request.method == 'POST':
        try:
            data = request.get_json()

            system = {
                'timezone': data.get('timezone', 'Asia/Kuala_Lumpur'),
                'school_name': data.get('school_name', 'Spring Gate Private School'),
                'school_country': data.get('school_country', 'Malaysia')
            }

            SystemSettings.save_setting('system', system)

            AuditLogger.log_action(request.current_user['id'], 'system_settings_updated',
                                  resource_type='settings',
                                  details={'timezone': system['timezone']},
                                  ip_address=get_client_ip())

            return jsonify({'success': True, 'message': 'System settings saved'}), 200

        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    system = SystemSettings.get_setting('system', SystemSettings.get_defaults()['system'])
    return render_template('admin/settings_system.html', system=system, user=request.current_user)


# Common timezones list for dropdown
COMMON_TIMEZONES = [
    ('Pacific/Midway', 'UTC-11:00 - Midway Island'),
    ('Pacific/Honolulu', 'UTC-10:00 - Hawaii'),
    ('America/Anchorage', 'UTC-09:00 - Alaska'),
    ('America/Los_Angeles', 'UTC-08:00 - Pacific Time (US & Canada)'),
    ('America/Denver', 'UTC-07:00 - Mountain Time (US & Canada)'),
    ('America/Chicago', 'UTC-06:00 - Central Time (US & Canada)'),
    ('America/New_York', 'UTC-05:00 - Eastern Time (US & Canada)'),
    ('America/Sao_Paulo', 'UTC-03:00 - Brasilia'),
    ('Atlantic/Azores', 'UTC-01:00 - Azores'),
    ('UTC', 'UTC+00:00 - UTC'),
    ('Europe/London', 'UTC+00:00 - London'),
    ('Europe/Paris', 'UTC+01:00 - Paris, Berlin'),
    ('Europe/Istanbul', 'UTC+03:00 - Istanbul'),
    ('Asia/Dubai', 'UTC+04:00 - Dubai'),
    ('Asia/Karachi', 'UTC+05:00 - Pakistan'),
    ('Asia/Kolkata', 'UTC+05:30 - India'),
    ('Asia/Dhaka', 'UTC+06:00 - Bangladesh'),
    ('Asia/Bangkok', 'UTC+07:00 - Bangkok'),
    ('Asia/Singapore', 'UTC+08:00 - Singapore'),
    ('Asia/Kuala_Lumpur', 'UTC+08:00 - Kuala Lumpur'),
    ('Asia/Hong_Kong', 'UTC+08:00 - Hong Kong'),
    ('Asia/Shanghai', 'UTC+08:00 - China'),
    ('Asia/Tokyo', 'UTC+09:00 - Tokyo'),
    ('Australia/Sydney', 'UTC+10:00 - Sydney'),
    ('Pacific/Auckland', 'UTC+12:00 - Auckland'),
]


def get_timezone_list():
    """Return list of common timezones for templates"""
    return COMMON_TIMEZONES


def get_grade_from_percentage(percentage: float) -> tuple:
    """Get grade label and level from percentage"""
    thresholds = SystemSettings.get_setting('marking_thresholds', SystemSettings.get_defaults()['marking_thresholds'])
    labels = SystemSettings.get_setting('grade_labels', SystemSettings.get_defaults()['grade_labels'])

    if percentage >= thresholds['excellent']:
        return labels['excellent'], 'excellent'
    elif percentage >= thresholds['good']:
        return labels['good'], 'good'
    elif percentage >= thresholds['satisfactory']:
        return labels['satisfactory'], 'satisfactory'
    else:
        return labels['needs_improvement'], 'needs_improvement'
