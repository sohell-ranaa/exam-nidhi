"""
Y6 Practice Exam - Email Service
SMTP configuration and email sending with magic links
"""

import smtplib
import secrets
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dbs.connection import get_connection
from src.core.cache import get_cache, cache_key


class EmailSettings:
    """Manage SMTP settings stored in database"""

    SETTINGS_KEY = 'smtp_settings'
    CACHE_KEY = 'settings:smtp'

    @classmethod
    def get_settings(cls) -> Dict[str, Any]:
        """Get SMTP settings from database or cache"""
        cache = get_cache()

        # Check cache first
        cached = cache.get(cls.CACHE_KEY)
        if cached:
            return cached

        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            cursor.execute("""
                SELECT setting_value FROM system_settings WHERE setting_key = %s
            """, (cls.SETTINGS_KEY,))
            result = cursor.fetchone()

            if result and result['setting_value']:
                settings = json.loads(result['setting_value'])
            else:
                # Default settings
                settings = {
                    'smtp_host': '',
                    'smtp_port': 587,
                    'smtp_user': '',
                    'smtp_password': '',
                    'smtp_from_email': '',
                    'smtp_from_name': 'Y6 Practice Exam',
                    'smtp_use_tls': True,
                    'smtp_enabled': False
                }

            # Cache for 1 hour
            cache.set(cls.CACHE_KEY, settings, 3600)
            return settings

        finally:
            cursor.close()
            conn.close()

    @classmethod
    def save_settings(cls, settings: Dict[str, Any]) -> bool:
        """Save SMTP settings to database"""
        conn = get_connection()
        cursor = conn.cursor()

        try:
            settings_json = json.dumps(settings)

            cursor.execute("""
                INSERT INTO system_settings (setting_key, setting_value, updated_at)
                VALUES (%s, %s, NOW())
                ON DUPLICATE KEY UPDATE setting_value = %s, updated_at = NOW()
            """, (cls.SETTINGS_KEY, settings_json, settings_json))

            conn.commit()

            # Clear cache
            cache = get_cache()
            cache.delete(cls.CACHE_KEY)

            return True

        except Exception as e:
            print(f"Save settings error: {e}")
            return False

        finally:
            cursor.close()
            conn.close()

    @classmethod
    def test_connection(cls, settings: Dict[str, Any]) -> tuple:
        """Test SMTP connection"""
        try:
            port = int(settings.get('smtp_port', 587))

            # Port 465 = SMTP_SSL (implicit TLS)
            # Port 25/587 = SMTP with optional STARTTLS
            if port == 465:
                server = smtplib.SMTP_SSL(settings['smtp_host'], port, timeout=10)
            else:
                server = smtplib.SMTP(settings['smtp_host'], port, timeout=10)
                # Try STARTTLS if available
                try:
                    server.starttls()
                except:
                    pass  # Server doesn't support STARTTLS

            if settings.get('smtp_user') and settings.get('smtp_password'):
                server.login(settings['smtp_user'], settings['smtp_password'])

            server.quit()
            return True, "Connection successful"

        except smtplib.SMTPAuthenticationError:
            return False, "Authentication failed - check username/password"
        except smtplib.SMTPConnectError:
            return False, "Could not connect to SMTP server"
        except Exception as e:
            return False, str(e)


class MagicLinkManager:
    """Manage magic links for email-based authentication"""

    LINK_VALIDITY_HOURS = 72  # 3 days

    @classmethod
    def create_magic_link(cls, user_id: int, exam_id: int, purpose: str = 'exam_attempt') -> Optional[str]:
        """Create a magic link token for exam access"""
        token = secrets.token_urlsafe(32)
        expires_at = datetime.now() + timedelta(hours=cls.LINK_VALIDITY_HOURS)

        conn = get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO magic_links (token, user_id, exam_id, purpose, expires_at, created_at)
                VALUES (%s, %s, %s, %s, %s, NOW())
            """, (token, user_id, exam_id, purpose, expires_at))
            conn.commit()

            return token

        except Exception as e:
            print(f"Create magic link error: {e}")
            return None

        finally:
            cursor.close()
            conn.close()

    @classmethod
    def validate_magic_link(cls, token: str) -> Optional[Dict[str, Any]]:
        """Validate and consume a magic link"""
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            cursor.execute("""
                SELECT ml.*, u.email, u.full_name, u.role_id,
                       pe.status as exam_status, qs.title as exam_title
                FROM magic_links ml
                JOIN users u ON ml.user_id = u.id
                LEFT JOIN practice_exams pe ON ml.exam_id = pe.id
                LEFT JOIN question_sets qs ON pe.question_set_id = qs.id
                WHERE ml.token = %s AND ml.used_at IS NULL AND ml.expires_at > NOW()
            """, (token,))
            link = cursor.fetchone()

            if not link:
                return None

            # Mark as used
            cursor.execute("""
                UPDATE magic_links SET used_at = NOW() WHERE token = %s
            """, (token,))
            conn.commit()

            return link

        finally:
            cursor.close()
            conn.close()


class EmailService:
    """Send emails using SMTP"""

    @classmethod
    def send_email(cls, to_email: str, subject: str, html_body: str, text_body: str = None) -> tuple:
        """Send an email"""
        settings = EmailSettings.get_settings()

        if not settings.get('smtp_enabled'):
            return False, "Email is not enabled"

        if not settings.get('smtp_host'):
            return False, "SMTP not configured"

        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"{settings.get('smtp_from_name', 'Y6 Practice Exam')} <{settings['smtp_from_email']}>"
            msg['To'] = to_email

            # Add text and HTML parts
            if text_body:
                msg.attach(MIMEText(text_body, 'plain'))
            msg.attach(MIMEText(html_body, 'html'))

            # Connect and send
            port = int(settings.get('smtp_port', 587))

            # Port 465 = SMTP_SSL (implicit TLS)
            # Port 25/587 = SMTP with optional STARTTLS
            if port == 465:
                server = smtplib.SMTP_SSL(settings['smtp_host'], port, timeout=30)
            else:
                server = smtplib.SMTP(settings['smtp_host'], port, timeout=30)
                # Try STARTTLS if available
                try:
                    server.starttls()
                except:
                    pass  # Server doesn't support STARTTLS

            if settings.get('smtp_user') and settings.get('smtp_password'):
                server.login(settings['smtp_user'], settings['smtp_password'])

            server.sendmail(settings['smtp_from_email'], [to_email], msg.as_string())
            server.quit()

            return True, "Email sent successfully"

        except Exception as e:
            print(f"Send email error: {e}")
            return False, str(e)

    @classmethod
    def send_exam_assignment(cls, student_email: str, student_name: str, exam_title: str,
                            subject_name: str, exam_date: str, deadline: str,
                            magic_link_token: str, base_url: str) -> tuple:
        """Send exam assignment notification with magic link"""

        magic_link_url = f"{base_url}/auth/magic/{magic_link_token}"

        subject = f"New Exam Assigned: {exam_title}"

        html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <!--[if mso]>
    <style type="text/css">
        table {{border-collapse: collapse;}}
        .button-link {{padding: 14px 28px !important;}}
    </style>
    <![endif]-->
</head>
<body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; line-height: 1.6; color: #323130; background-color: #f5f5f5;">
    <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="background-color: #f5f5f5;">
        <tr>
            <td style="padding: 20px;">
                <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="600" style="max-width: 600px; margin: 0 auto;">
                    <!-- Header -->
                    <tr>
                        <td style="background: #0078D4; padding: 30px 40px; text-align: center; border-radius: 8px 8px 0 0;">
                            <h1 style="margin: 0; font-size: 24px; font-weight: 600; color: #ffffff;">New Exam Assigned</h1>
                            <p style="margin: 10px 0 0; font-size: 14px; color: rgba(255,255,255,0.9);">Y6 Practice Exam System</p>
                        </td>
                    </tr>
                    <!-- Content -->
                    <tr>
                        <td style="background: #ffffff; padding: 30px 40px; border-left: 1px solid #e1dfdd; border-right: 1px solid #e1dfdd;">
                            <p style="margin: 0 0 16px; font-size: 16px; color: #323130;">Dear <strong>{student_name}</strong>,</p>
                            <p style="margin: 0 0 24px; font-size: 16px; color: #323130;">A new practice exam has been assigned to you. Please complete it before the deadline.</p>

                            <!-- Exam Details Card -->
                            <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="background: #f8f9fa; border-radius: 8px; margin-bottom: 24px;">
                                <tr>
                                    <td style="padding: 20px;">
                                        <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
                                            <tr>
                                                <td style="padding: 8px 0; font-weight: 600; color: #605e5c; width: 100px; font-size: 14px;">Exam:</td>
                                                <td style="padding: 8px 0; font-size: 14px; color: #323130;"><strong>{exam_title}</strong></td>
                                            </tr>
                                            <tr>
                                                <td style="padding: 8px 0; font-weight: 600; color: #605e5c; font-size: 14px;">Subject:</td>
                                                <td style="padding: 8px 0; font-size: 14px; color: #323130;">{subject_name}</td>
                                            </tr>
                                            <tr>
                                                <td style="padding: 8px 0; font-weight: 600; color: #605e5c; font-size: 14px;">Exam Date:</td>
                                                <td style="padding: 8px 0; font-size: 14px; color: #323130;">{exam_date}</td>
                                            </tr>
                                            <tr>
                                                <td style="padding: 8px 0; font-weight: 600; color: #605e5c; font-size: 14px;">Deadline:</td>
                                                <td style="padding: 8px 0; font-size: 14px;"><strong style="color: #c42b1c;">{deadline}</strong></td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                            </table>

                            <!-- Button -->
                            <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
                                <tr>
                                    <td style="text-align: center; padding: 10px 0 24px;">
                                        <a href="{magic_link_url}" class="button-link" style="display: inline-block; background-color: #0078D4; color: #ffffff; padding: 14px 32px; text-decoration: none; border-radius: 6px; font-weight: 600; font-size: 16px; mso-padding-alt: 0;">
                                            <!--[if mso]><i style="letter-spacing: 32px; mso-font-width: -100%; mso-text-raise: 30pt;">&nbsp;</i><![endif]-->
                                            <span style="mso-text-raise: 15pt;">Start Exam Now</span>
                                            <!--[if mso]><i style="letter-spacing: 32px; mso-font-width: -100%;">&nbsp;</i><![endif]-->
                                        </a>
                                    </td>
                                </tr>
                            </table>

                            <!-- Warning -->
                            <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="margin-bottom: 24px;">
                                <tr>
                                    <td style="background: #fff8e5; border-left: 4px solid #ffb900; padding: 12px 16px; border-radius: 0 4px 4px 0;">
                                        <p style="margin: 0; font-size: 14px; color: #5c5346;"><strong>Note:</strong> This link is valid for 72 hours and can only be used once. After clicking, you will be automatically logged in and directed to the exam.</p>
                                    </td>
                                </tr>
                            </table>

                            <p style="margin: 0 0 8px; font-size: 14px; color: #605e5c;">If the button doesn't work, copy and paste this link into your browser:</p>
                            <p style="margin: 0; font-size: 12px; color: #0078D4; word-break: break-all;">{magic_link_url}</p>
                        </td>
                    </tr>
                    <!-- Footer -->
                    <tr>
                        <td style="background: #faf9f8; padding: 24px 40px; text-align: center; border: 1px solid #e1dfdd; border-top: none; border-radius: 0 0 8px 8px;">
                            <p style="margin: 0 0 4px; font-size: 13px; color: #605e5c;">Spring Gate Private School, Selangor, Malaysia</p>
                            <p style="margin: 0; font-size: 12px; color: #8a8886;">Y6 Practice Exam System</p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
"""

        text_body = f"""
Dear {student_name},

A new practice exam has been assigned to you:

Exam: {exam_title}
Subject: {subject_name}
Exam Date: {exam_date}
Deadline: {deadline}

Click the link below to start your exam:
{magic_link_url}

This link is valid for 72 hours and can only be used once.

Best regards,
Spring Gate Private School
Y6 Practice Exam System
"""

        return cls.send_email(student_email, subject, html_body, text_body)

    @classmethod
    def send_results_released(cls, student_email: str, student_name: str, exam_title: str,
                             score: float, percentage: float, base_url: str) -> tuple:
        """Send notification when exam results are released"""

        subject = f"Exam Results Released: {exam_title}"

        # Determine grade color and background
        if percentage >= 80:
            grade_color = "#107C10"
            grade_bg = "#dff6dd"
            grade_text = "Excellent!"
            header_bg = "#107C10"
        elif percentage >= 60:
            grade_color = "#0078D4"
            grade_bg = "#deecf9"
            grade_text = "Good job!"
            header_bg = "#0078D4"
        elif percentage >= 40:
            grade_color = "#835c00"
            grade_bg = "#fff4ce"
            grade_text = "Keep practicing!"
            header_bg = "#c19c00"
        else:
            grade_color = "#c42b1c"
            grade_bg = "#fde7e9"
            grade_text = "More practice needed"
            header_bg = "#d13438"

        html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <!--[if mso]>
    <style type="text/css">
        table {{border-collapse: collapse;}}
        .button-link {{padding: 14px 28px !important;}}
    </style>
    <![endif]-->
</head>
<body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; line-height: 1.6; color: #323130; background-color: #f5f5f5;">
    <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="background-color: #f5f5f5;">
        <tr>
            <td style="padding: 20px;">
                <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="600" style="max-width: 600px; margin: 0 auto;">
                    <!-- Header -->
                    <tr>
                        <td style="background: {header_bg}; padding: 30px 40px; text-align: center; border-radius: 8px 8px 0 0;">
                            <h1 style="margin: 0; font-size: 24px; font-weight: 600; color: #ffffff;">Results Released</h1>
                            <p style="margin: 10px 0 0; font-size: 14px; color: rgba(255,255,255,0.9);">{exam_title}</p>
                        </td>
                    </tr>
                    <!-- Content -->
                    <tr>
                        <td style="background: #ffffff; padding: 30px 40px; border-left: 1px solid #e1dfdd; border-right: 1px solid #e1dfdd;">
                            <p style="margin: 0 0 16px; font-size: 16px; color: #323130;">Dear <strong>{student_name}</strong>,</p>
                            <p style="margin: 0 0 24px; font-size: 16px; color: #323130;">Your exam results have been released! Here's how you did:</p>

                            <!-- Score Card -->
                            <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="background: {grade_bg}; border-radius: 12px; margin-bottom: 24px;">
                                <tr>
                                    <td style="padding: 32px; text-align: center;">
                                        <p style="margin: 0; font-size: 56px; font-weight: 700; color: {grade_color}; line-height: 1;">{percentage:.1f}%</p>
                                        <p style="margin: 12px 0 0; font-size: 18px; font-weight: 600; color: {grade_color};">{grade_text}</p>
                                        <p style="margin: 16px 0 0; font-size: 14px; color: #605e5c;">Score: {score} marks</p>
                                    </td>
                                </tr>
                            </table>

                            <!-- Button -->
                            <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
                                <tr>
                                    <td style="text-align: center; padding: 10px 0 16px;">
                                        <a href="{base_url}/student/dashboard" class="button-link" style="display: inline-block; background-color: #0078D4; color: #ffffff; padding: 14px 32px; text-decoration: none; border-radius: 6px; font-weight: 600; font-size: 16px; mso-padding-alt: 0;">
                                            <!--[if mso]><i style="letter-spacing: 32px; mso-font-width: -100%; mso-text-raise: 30pt;">&nbsp;</i><![endif]-->
                                            <span style="mso-text-raise: 15pt;">View Detailed Results</span>
                                            <!--[if mso]><i style="letter-spacing: 32px; mso-font-width: -100%;">&nbsp;</i><![endif]-->
                                        </a>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    <!-- Footer -->
                    <tr>
                        <td style="background: #faf9f8; padding: 24px 40px; text-align: center; border: 1px solid #e1dfdd; border-top: none; border-radius: 0 0 8px 8px;">
                            <p style="margin: 0 0 4px; font-size: 13px; color: #605e5c;">Spring Gate Private School, Selangor, Malaysia</p>
                            <p style="margin: 0; font-size: 12px; color: #8a8886;">Y6 Practice Exam System</p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
"""

        text_body = f"""
Dear {student_name},

Your exam results for "{exam_title}" have been released!

Score: {percentage:.1f}% ({score} marks)
{grade_text}

Log in to view your detailed results: {base_url}/student/dashboard

Best regards,
Spring Gate Private School
Y6 Practice Exam System
"""

        return cls.send_email(student_email, subject, html_body, text_body)

    @classmethod
    def send_test_email(cls, to_email: str) -> tuple:
        """Send a test email to verify SMTP configuration"""

        subject = "Test Email - Y6 Practice Exam System"

        html_body = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; line-height: 1.6; color: #323130; background-color: #f5f5f5;">
    <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="background-color: #f5f5f5;">
        <tr>
            <td style="padding: 20px;">
                <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="600" style="max-width: 600px; margin: 0 auto;">
                    <!-- Header -->
                    <tr>
                        <td style="background: #0078D4; padding: 30px 40px; text-align: center; border-radius: 8px 8px 0 0;">
                            <h1 style="margin: 0; font-size: 24px; font-weight: 600; color: #ffffff;">Test Email</h1>
                            <p style="margin: 10px 0 0; font-size: 14px; color: rgba(255,255,255,0.9);">Y6 Practice Exam System</p>
                        </td>
                    </tr>
                    <!-- Content -->
                    <tr>
                        <td style="background: #ffffff; padding: 30px 40px; border-left: 1px solid #e1dfdd; border-right: 1px solid #e1dfdd;">
                            <!-- Success Box -->
                            <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="margin-bottom: 24px;">
                                <tr>
                                    <td style="background: #dff6dd; border-left: 4px solid #107C10; padding: 16px 20px; border-radius: 0 6px 6px 0;">
                                        <p style="margin: 0; font-size: 16px; color: #0e700e;"><strong>Success!</strong> Your email configuration is working correctly.</p>
                                    </td>
                                </tr>
                            </table>

                            <p style="margin: 0 0 16px; font-size: 16px; color: #323130;">This is a test email from the Y6 Practice Exam System to verify that your SMTP settings are configured properly.</p>
                            <p style="margin: 0 0 12px; font-size: 16px; color: #323130;">If you received this email, it means:</p>
                            <table role="presentation" cellspacing="0" cellpadding="0" border="0" style="margin-bottom: 16px;">
                                <tr>
                                    <td style="padding: 6px 0; font-size: 15px; color: #323130;">&#x2022; SMTP server connection is working</td>
                                </tr>
                                <tr>
                                    <td style="padding: 6px 0; font-size: 15px; color: #323130;">&#x2022; Authentication is successful</td>
                                </tr>
                                <tr>
                                    <td style="padding: 6px 0; font-size: 15px; color: #323130;">&#x2022; Emails can be sent to recipients</td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    <!-- Footer -->
                    <tr>
                        <td style="background: #faf9f8; padding: 24px 40px; text-align: center; border: 1px solid #e1dfdd; border-top: none; border-radius: 0 0 8px 8px;">
                            <p style="margin: 0 0 4px; font-size: 13px; color: #605e5c;">Spring Gate Private School, Selangor, Malaysia</p>
                            <p style="margin: 0; font-size: 12px; color: #8a8886;">Y6 Practice Exam System</p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
"""

        text_body = """
Test Email - Y6 Practice Exam System

Success! Your email configuration is working correctly.

This is a test email from the Y6 Practice Exam System to verify that your SMTP settings are configured properly.

If you received this email, it means:
- SMTP server connection is working
- Authentication is successful
- Emails can be sent to recipients

Spring Gate Private School, Selangor, Malaysia
Y6 Practice Exam System
"""

        return cls.send_email(to_email, subject, html_body, text_body)

    @classmethod
    def send_password_reset(cls, student_email: str, student_name: str,
                           reset_token: str, base_url: str) -> tuple:
        """Send password reset email with magic link"""

        reset_url = f"{base_url}/auth/reset-password/{reset_token}"

        subject = "Password Reset - Y6 Practice Exam"

        html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <!--[if mso]>
    <style type="text/css">
        table {{border-collapse: collapse;}}
        .button-link {{padding: 14px 28px !important;}}
    </style>
    <![endif]-->
</head>
<body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; line-height: 1.6; color: #323130; background-color: #f5f5f5;">
    <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="background-color: #f5f5f5;">
        <tr>
            <td style="padding: 20px;">
                <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="600" style="max-width: 600px; margin: 0 auto;">
                    <!-- Header -->
                    <tr>
                        <td style="background: #5c2d91; padding: 30px 40px; text-align: center; border-radius: 8px 8px 0 0;">
                            <h1 style="margin: 0; font-size: 24px; font-weight: 600; color: #ffffff;">Password Reset</h1>
                            <p style="margin: 10px 0 0; font-size: 14px; color: rgba(255,255,255,0.9);">Y6 Practice Exam System</p>
                        </td>
                    </tr>
                    <!-- Content -->
                    <tr>
                        <td style="background: #ffffff; padding: 30px 40px; border-left: 1px solid #e1dfdd; border-right: 1px solid #e1dfdd;">
                            <p style="margin: 0 0 16px; font-size: 16px; color: #323130;">Dear <strong>{student_name}</strong>,</p>
                            <p style="margin: 0 0 24px; font-size: 16px; color: #323130;">We received a request to reset your password. Click the button below to set a new password:</p>

                            <!-- Button -->
                            <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
                                <tr>
                                    <td style="text-align: center; padding: 10px 0 24px;">
                                        <a href="{reset_url}" class="button-link" style="display: inline-block; background-color: #107C10; color: #ffffff; padding: 14px 32px; text-decoration: none; border-radius: 6px; font-weight: 600; font-size: 16px; mso-padding-alt: 0;">
                                            <!--[if mso]><i style="letter-spacing: 32px; mso-font-width: -100%; mso-text-raise: 30pt;">&nbsp;</i><![endif]-->
                                            <span style="mso-text-raise: 15pt;">Reset Password</span>
                                            <!--[if mso]><i style="letter-spacing: 32px; mso-font-width: -100%;">&nbsp;</i><![endif]-->
                                        </a>
                                    </td>
                                </tr>
                            </table>

                            <!-- Warning -->
                            <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="margin-bottom: 24px;">
                                <tr>
                                    <td style="background: #fff8e5; border-left: 4px solid #ffb900; padding: 12px 16px; border-radius: 0 4px 4px 0;">
                                        <p style="margin: 0; font-size: 14px; color: #5c5346;"><strong>Note:</strong> This link is valid for 72 hours and can only be used once. If you didn't request a password reset, you can safely ignore this email.</p>
                                    </td>
                                </tr>
                            </table>

                            <p style="margin: 0 0 8px; font-size: 14px; color: #605e5c;">If the button doesn't work, copy and paste this link into your browser:</p>
                            <p style="margin: 0; font-size: 12px; color: #0078D4; word-break: break-all;">{reset_url}</p>
                        </td>
                    </tr>
                    <!-- Footer -->
                    <tr>
                        <td style="background: #faf9f8; padding: 24px 40px; text-align: center; border: 1px solid #e1dfdd; border-top: none; border-radius: 0 0 8px 8px;">
                            <p style="margin: 0 0 4px; font-size: 13px; color: #605e5c;">Spring Gate Private School, Selangor, Malaysia</p>
                            <p style="margin: 0; font-size: 12px; color: #8a8886;">Y6 Practice Exam System</p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
"""

        text_body = f"""
Dear {student_name},

We received a request to reset your password.

Click the link below to set a new password:
{reset_url}

This link is valid for 72 hours and can only be used once.

If you didn't request a password reset, you can safely ignore this email.

Best regards,
Spring Gate Private School
Y6 Practice Exam System
"""

        return cls.send_email(student_email, subject, html_body, text_body)
