"""
Y6 Practice Exam - Admin Routes
Dashboard, exam management, grading with pagination and search
"""

from flask import Blueprint, request, jsonify, render_template, redirect, url_for
from datetime import datetime, date
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src" / "core"))
sys.path.insert(0, str(PROJECT_ROOT / "dbs"))

from src.core.auth import login_required, role_required, AuditLogger, UserManager, PasswordManager, get_client_ip
from src.core.pagination import Paginator, paginate_query
from src.core.cache import get_cache, cache_key
from dbs.connection import get_connection

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


def get_base_url():
    """Get base URL for email links"""
    return request.url_root.rstrip('/')


@admin_bp.route('/')
@admin_bp.route('/dashboard')
@role_required('Admin')
def dashboard():
    """Admin dashboard with overview stats"""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # Get stats
        cursor.execute("SELECT COUNT(*) as count FROM users WHERE role_id = 2 AND is_active = TRUE")
        student_count = cursor.fetchone()['count']

        cursor.execute("SELECT COUNT(*) as count FROM question_sets WHERE is_active = TRUE")
        question_set_count = cursor.fetchone()['count']

        cursor.execute("SELECT COUNT(*) as count FROM practice_exams WHERE status = 'submitted'")
        pending_grading = cursor.fetchone()['count']

        cursor.execute("SELECT COUNT(*) as count FROM practice_exams WHERE status = 'released'")
        completed_exams = cursor.fetchone()['count']

        cursor.execute("SELECT AVG(percentage) as avg FROM practice_exams WHERE status = 'released'")
        avg_score = cursor.fetchone()['avg'] or 0

        # Recent submissions (including released ones)
        cursor.execute("""
            SELECT pe.*, u.full_name as student_name, qs.title as exam_title, s.name as subject_name
            FROM practice_exams pe
            JOIN users u ON pe.student_id = u.id
            JOIN question_sets qs ON pe.question_set_id = qs.id
            JOIN subjects s ON qs.subject_id = s.id
            WHERE pe.status IN ('submitted', 'grading', 'released')
            ORDER BY COALESCE(pe.released_at, pe.submitted_at, pe.created_at) DESC
            LIMIT 10
        """)
        recent_submissions = cursor.fetchall()

        # Upcoming deadlines
        cursor.execute("""
            SELECT pe.*, u.full_name as student_name, qs.title as exam_title
            FROM practice_exams pe
            JOIN users u ON pe.student_id = u.id
            JOIN question_sets qs ON pe.question_set_id = qs.id
            WHERE pe.status IN ('pending', 'in_progress') AND pe.deadline IS NOT NULL
            ORDER BY pe.deadline ASC
            LIMIT 5
        """)
        upcoming_deadlines = cursor.fetchall()

        # Format dates
        for sub in recent_submissions:
            if sub.get('released_at'):
                sub['display_date'] = sub['released_at'].strftime('%d %b %Y %H:%M')
            elif sub.get('submitted_at'):
                sub['display_date'] = sub['submitted_at'].strftime('%d %b %Y %H:%M')
            else:
                sub['display_date'] = ''
            if sub['submitted_at']:
                sub['submitted_at'] = sub['submitted_at'].strftime('%d %b %Y %H:%M')
            if sub['exam_date']:
                sub['exam_date'] = sub['exam_date'].strftime('%d %b %Y')

        for deadline in upcoming_deadlines:
            if deadline['deadline']:
                deadline['deadline'] = deadline['deadline'].strftime('%d %b %Y %H:%M')

        return render_template('admin/dashboard.html',
                             student_count=student_count,
                             question_set_count=question_set_count,
                             pending_grading=pending_grading,
                             completed_exams=completed_exams,
                             avg_score=round(avg_score, 1),
                             recent_submissions=recent_submissions,
                             upcoming_deadlines=upcoming_deadlines,
                             user=request.current_user)

    finally:
        cursor.close()
        conn.close()


@admin_bp.route('/students')
@role_required('Admin')
def students():
    """Manage students with pagination and search"""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # Get query params
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 20))
    search = request.args.get('search', '').strip()
    status = request.args.get('status', 'all')

    try:
        # Build query
        where_clauses = ["u.role_id = 2"]
        params = []

        if search:
            where_clauses.append("(u.full_name LIKE %s OR u.email LIKE %s)")
            params.extend([f'%{search}%', f'%{search}%'])

        if status == 'active':
            where_clauses.append("u.is_active = TRUE")
        elif status == 'inactive':
            where_clauses.append("u.is_active = FALSE")

        where_sql = " AND ".join(where_clauses)

        # Count query
        cursor.execute(f"SELECT COUNT(*) as count FROM users u WHERE {where_sql}", params)
        total = cursor.fetchone()['count']

        # Create paginator
        paginator = Paginator(total, page, per_page)

        # Data query
        cursor.execute(f"""
            SELECT u.*,
                   (SELECT COUNT(*) FROM practice_exams WHERE student_id = u.id) as exam_count,
                   (SELECT AVG(percentage) FROM practice_exams WHERE student_id = u.id AND status = 'released') as avg_score,
                   (SELECT COUNT(*) FROM practice_exams WHERE student_id = u.id AND status = 'submitted') as pending_count
            FROM users u
            WHERE {where_sql}
            ORDER BY u.created_at DESC
            LIMIT %s OFFSET %s
        """, params + [paginator.limit, paginator.offset])
        students = cursor.fetchall()

        for student in students:
            if student['created_at']:
                student['created_at'] = student['created_at'].strftime('%d %b %Y')
            if student['last_login']:
                student['last_login'] = student['last_login'].strftime('%d %b %Y %H:%M')

        return render_template('admin/students.html',
                             students=students,
                             pagination=paginator.to_dict(),
                             search=search,
                             status=status,
                             user=request.current_user)

    finally:
        cursor.close()
        conn.close()


@admin_bp.route('/students/create', methods=['POST'])
@role_required('Admin')
def create_student():
    """Create a new student account"""
    try:
        data = request.get_json()

        email = data.get('email', '').strip().lower()
        full_name = data.get('full_name', '').strip()
        password = data.get('password', '')

        if not email or not full_name or not password:
            return jsonify({'success': False, 'error': 'All fields are required'}), 400

        if len(password) < 6:
            return jsonify({'success': False, 'error': 'Password must be at least 6 characters'}), 400

        # Email validation
        import re
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            return jsonify({'success': False, 'error': 'Invalid email format'}), 400

        # Check if email exists
        existing = UserManager.get_user_by_email(email)
        if existing:
            return jsonify({'success': False, 'error': 'Email already exists'}), 400

        # Create student (role_id = 2)
        user_id = UserManager.create_user(email, password, full_name, role_id=2, created_by=request.current_user['id'])

        AuditLogger.log_action(request.current_user['id'], 'student_created',
                              resource_type='user', resource_id=str(user_id),
                              details={'email': email, 'full_name': full_name},
                              ip_address=get_client_ip())

        return jsonify({'success': True, 'message': 'Student created successfully', 'id': user_id}), 200

    except Exception as e:
        print(f"Create student error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/students/<int:student_id>/toggle', methods=['POST'])
@role_required('Admin')
def toggle_student(student_id):
    """Toggle student active status"""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("UPDATE users SET is_active = NOT is_active WHERE id = %s AND role_id = 2", (student_id,))
        conn.commit()

        cursor.close()
        conn.close()

        AuditLogger.log_action(request.current_user['id'], 'student_toggled',
                              resource_type='user', resource_id=str(student_id),
                              ip_address=get_client_ip())

        return jsonify({'success': True, 'message': 'Student status updated'}), 200

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/students/<int:student_id>')
@role_required('Admin')
def get_student(student_id):
    """Get student details with statistics"""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # Get student info
        cursor.execute("""
            SELECT id, email, full_name, is_active, last_login, created_at
            FROM users WHERE id = %s AND role_id = 2
        """, (student_id,))
        student = cursor.fetchone()

        if not student:
            return jsonify({'success': False, 'error': 'Student not found'}), 404

        # Format dates
        if student['last_login']:
            student['last_login'] = student['last_login'].strftime('%d %b %Y %H:%M')
        if student['created_at']:
            student['created_at'] = student['created_at'].strftime('%d %b %Y')

        # Get overall statistics
        cursor.execute("""
            SELECT
                COUNT(*) as total_exams,
                SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending_exams,
                SUM(CASE WHEN status = 'in_progress' THEN 1 ELSE 0 END) as in_progress_exams,
                SUM(CASE WHEN status IN ('submitted', 'grading') THEN 1 ELSE 0 END) as needs_grading,
                SUM(CASE WHEN status = 'released' THEN 1 ELSE 0 END) as completed_exams,
                AVG(CASE WHEN status = 'released' THEN percentage ELSE NULL END) as avg_score,
                MAX(CASE WHEN status = 'released' THEN percentage ELSE NULL END) as best_score,
                MIN(CASE WHEN status = 'released' THEN percentage ELSE NULL END) as lowest_score
            FROM practice_exams WHERE student_id = %s
        """, (student_id,))
        stats = cursor.fetchone()

        # Get subject-wise performance
        cursor.execute("""
            SELECT
                s.name as subject_name,
                s.code as subject_code,
                COUNT(*) as exam_count,
                AVG(pe.percentage) as avg_score,
                MAX(pe.percentage) as best_score
            FROM practice_exams pe
            JOIN question_sets qs ON pe.question_set_id = qs.id
            JOIN subjects s ON qs.subject_id = s.id
            WHERE pe.student_id = %s AND pe.status = 'released'
            GROUP BY s.id, s.name, s.code
            ORDER BY s.name
        """, (student_id,))
        subject_stats = cursor.fetchall()

        # Get recent exams
        cursor.execute("""
            SELECT pe.id, pe.status, pe.exam_date, pe.percentage,
                   qs.title as exam_title, s.name as subject_name, s.code as subject_code
            FROM practice_exams pe
            JOIN question_sets qs ON pe.question_set_id = qs.id
            JOIN subjects s ON qs.subject_id = s.id
            WHERE pe.student_id = %s
            ORDER BY pe.created_at DESC
            LIMIT 10
        """, (student_id,))
        recent_exams = cursor.fetchall()

        for exam in recent_exams:
            if exam['exam_date']:
                exam['exam_date'] = exam['exam_date'].strftime('%d %b %Y')

        return jsonify({
            'success': True,
            'student': student,
            'stats': stats,
            'subject_stats': subject_stats,
            'recent_exams': recent_exams
        }), 200

    finally:
        cursor.close()
        conn.close()


@admin_bp.route('/students/<int:student_id>/update', methods=['POST'])
@role_required('Admin')
def update_student(student_id):
    """Update student details"""
    try:
        data = request.get_json()
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        # Verify student exists
        cursor.execute("SELECT id, email FROM users WHERE id = %s AND role_id = 2", (student_id,))
        student = cursor.fetchone()

        if not student:
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'error': 'Student not found'}), 404

        updates = []
        params = []

        # Update full name
        if 'full_name' in data and data['full_name'].strip():
            updates.append("full_name = %s")
            params.append(data['full_name'].strip())

        # Update email
        if 'email' in data and data['email'].strip():
            new_email = data['email'].strip().lower()
            import re
            if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', new_email):
                cursor.close()
                conn.close()
                return jsonify({'success': False, 'error': 'Invalid email format'}), 400

            # Check if email is taken by another user
            if new_email != student['email']:
                cursor.execute("SELECT id FROM users WHERE email = %s AND id != %s", (new_email, student_id))
                if cursor.fetchone():
                    cursor.close()
                    conn.close()
                    return jsonify({'success': False, 'error': 'Email already in use'}), 400

            updates.append("email = %s")
            params.append(new_email)

        if not updates:
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'error': 'No fields to update'}), 400

        params.append(student_id)
        cursor.execute(f"UPDATE users SET {', '.join(updates)} WHERE id = %s", params)
        conn.commit()

        AuditLogger.log_action(request.current_user['id'], 'student_updated',
                              resource_type='user', resource_id=str(student_id),
                              details=data, ip_address=get_client_ip())

        cursor.close()
        conn.close()

        return jsonify({'success': True, 'message': 'Student updated successfully'}), 200

    except Exception as e:
        print(f"Update student error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/students/<int:student_id>/reset-password', methods=['POST'])
@role_required('Admin')
def reset_student_password(student_id):
    """Send password reset link to student"""
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT id, email, full_name FROM users WHERE id = %s AND role_id = 2", (student_id,))
        student = cursor.fetchone()

        if not student:
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'error': 'Student not found'}), 404

        cursor.close()
        conn.close()

        # Generate and send password reset link
        from src.core.email import MagicLinkManager, EmailService, EmailSettings

        smtp_settings = EmailSettings.get_settings()
        if not smtp_settings.get('smtp_enabled'):
            return jsonify({'success': False, 'error': 'Email is not configured. Please set up SMTP settings.'}), 400

        # Create magic link for password reset
        token = MagicLinkManager.create_magic_link(student_id, None, 'password_reset')

        if token:
            success, message = EmailService.send_password_reset(
                student_email=student['email'],
                student_name=student['full_name'],
                reset_token=token,
                base_url=get_base_url()
            )

            if success:
                AuditLogger.log_action(request.current_user['id'], 'password_reset_sent',
                                      resource_type='user', resource_id=str(student_id),
                                      details={'email': student['email']},
                                      ip_address=get_client_ip())

                return jsonify({'success': True, 'message': f'Password reset link sent to {student["email"]}'}), 200
            else:
                return jsonify({'success': False, 'error': message or 'Failed to send email'}), 500
        else:
            return jsonify({'success': False, 'error': 'Failed to create reset link'}), 500

    except Exception as e:
        print(f"Reset password error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/students/<int:student_id>/set-password', methods=['POST'])
@role_required('Admin')
def set_student_password(student_id):
    """Directly set a new password for student"""
    try:
        data = request.get_json()
        new_password = data.get('password', '')

        if len(new_password) < 6:
            return jsonify({'success': False, 'error': 'Password must be at least 6 characters'}), 400

        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT id FROM users WHERE id = %s AND role_id = 2", (student_id,))
        if not cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'error': 'Student not found'}), 404

        # Hash and update password
        password_hash = PasswordManager.hash_password(new_password)
        cursor.execute("UPDATE users SET password_hash = %s WHERE id = %s", (password_hash, student_id))
        conn.commit()

        AuditLogger.log_action(request.current_user['id'], 'password_changed_by_admin',
                              resource_type='user', resource_id=str(student_id),
                              ip_address=get_client_ip())

        cursor.close()
        conn.close()

        return jsonify({'success': True, 'message': 'Password updated successfully'}), 200

    except Exception as e:
        print(f"Set password error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/exams')
@role_required('Admin')
def exams():
    """Manage exams with pagination and filters"""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # Get query params
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 20))
    search = request.args.get('search', '').strip()
    subject_id = request.args.get('subject', '')
    status = request.args.get('status', 'all')

    try:
        # Get subjects for filter
        cursor.execute("SELECT * FROM subjects WHERE is_active = TRUE ORDER BY name")
        subjects = cursor.fetchall()

        # Build query
        where_clauses = ["1=1"]
        params = []

        if search:
            where_clauses.append("(qs.title LIKE %s OR u.full_name LIKE %s)")
            params.extend([f'%{search}%', f'%{search}%'])

        if subject_id:
            where_clauses.append("qs.subject_id = %s")
            params.append(subject_id)

        if status != 'all':
            where_clauses.append("pe.status = %s")
            params.append(status)

        where_sql = " AND ".join(where_clauses)

        # Count
        cursor.execute(f"""
            SELECT COUNT(*) as count FROM practice_exams pe
            JOIN question_sets qs ON pe.question_set_id = qs.id
            JOIN users u ON pe.student_id = u.id
            WHERE {where_sql}
        """, params)
        total = cursor.fetchone()['count']

        paginator = Paginator(total, page, per_page)

        # Get exams
        cursor.execute(f"""
            SELECT pe.*, u.full_name as student_name, u.email as student_email,
                   qs.title as exam_title, s.name as subject_name, s.code as subject_code
            FROM practice_exams pe
            JOIN users u ON pe.student_id = u.id
            JOIN question_sets qs ON pe.question_set_id = qs.id
            JOIN subjects s ON qs.subject_id = s.id
            WHERE {where_sql}
            ORDER BY pe.created_at DESC
            LIMIT %s OFFSET %s
        """, params + [paginator.limit, paginator.offset])
        exams = cursor.fetchall()

        now = datetime.now()
        for exam in exams:
            # Calculate display status for pending exams
            exam['display_status'] = exam['status']
            if exam['status'] == 'pending' and exam.get('scheduled_at'):
                scheduled = exam['scheduled_at']
                if scheduled > now:
                    time_until = (scheduled - now).total_seconds()
                    if time_until <= 3600:  # Within 1 hour
                        exam['display_status'] = 'soon'
                    else:
                        exam['display_status'] = 'scheduled'

            # Format dates for display (keep scheduled_at as datetime for template)
            if exam['deadline']:
                exam['deadline'] = exam['deadline'].strftime('%d %b %Y %H:%M')
            if exam['submitted_at']:
                exam['submitted_at'] = exam['submitted_at'].strftime('%d %b %Y %H:%M')

        # Get question sets for assignment
        cursor.execute("""
            SELECT qs.*, s.name as subject_name, s.code as subject_code,
                   (SELECT COUNT(*) FROM questions WHERE question_set_id = qs.id) as question_count
            FROM question_sets qs
            JOIN subjects s ON qs.subject_id = s.id
            WHERE qs.is_active = TRUE
            ORDER BY s.name, qs.title
        """)
        question_sets = cursor.fetchall()

        # Get students for assignment
        cursor.execute("SELECT id, full_name, email FROM users WHERE role_id = 2 AND is_active = TRUE ORDER BY full_name")
        students_list = cursor.fetchall()

        return render_template('admin/exams.html',
                             exams=exams,
                             subjects=subjects,
                             question_sets=question_sets,
                             students=students_list,
                             pagination=paginator.to_dict(),
                             search=search,
                             selected_subject=subject_id,
                             selected_status=status,
                             user=request.current_user)

    finally:
        cursor.close()
        conn.close()


@admin_bp.route('/exams/assign', methods=['POST'])
@role_required('Admin')
def assign_exam():
    """Assign exam to student with optional email notification"""
    try:
        data = request.get_json()

        student_id = data.get('student_id')
        question_set_id = data.get('question_set_id')
        exam_date = data.get('exam_date', date.today().isoformat())
        exam_datetime = data.get('exam_datetime')  # Full datetime string: "YYYY-MM-DD HH:MM:SS"
        deadline = data.get('deadline')
        send_email = data.get('send_email', True)

        # Parse scheduled_at from exam_datetime
        scheduled_at = None
        if exam_datetime:
            try:
                scheduled_at = datetime.strptime(exam_datetime, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                try:
                    scheduled_at = datetime.strptime(exam_datetime, '%Y-%m-%d %H:%M')
                except ValueError:
                    pass

        # Validate: scheduled time must be now or in the future
        now = datetime.now()
        if scheduled_at and scheduled_at < now:
            return jsonify({'success': False, 'error': 'Exam date and time must be in the future'}), 400

        # Validate: exam_date must be today or in the future
        if exam_date:
            exam_date_obj = datetime.strptime(exam_date, '%Y-%m-%d').date()
            if exam_date_obj < date.today():
                return jsonify({'success': False, 'error': 'Exam date must be today or in the future'}), 400

        if not student_id or not question_set_id:
            return jsonify({'success': False, 'error': 'Student and exam are required'}), 400

        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            # Get question set info for max_score
            cursor.execute("""
                SELECT qs.*, s.name as subject_name, SUM(q.marks) as total_marks
                FROM question_sets qs
                JOIN subjects s ON qs.subject_id = s.id
                LEFT JOIN questions q ON q.question_set_id = qs.id
                WHERE qs.id = %s
                GROUP BY qs.id
            """, (question_set_id,))
            question_set = cursor.fetchone()
            max_score = question_set['total_marks'] if question_set['total_marks'] else 50

            # Get student info
            cursor.execute("SELECT * FROM users WHERE id = %s", (student_id,))
            student = cursor.fetchone()

            # Create practice exam with scheduled_at
            cursor.execute("""
                INSERT INTO practice_exams (student_id, question_set_id, exam_date, scheduled_at, deadline, max_score, status)
                VALUES (%s, %s, %s, %s, %s, %s, 'pending')
            """, (student_id, question_set_id, exam_date, scheduled_at, deadline if deadline else None, max_score))

            conn.commit()
            exam_id = cursor.lastrowid

            # Send email with magic link if enabled
            email_sent = False
            if send_email and student['email']:
                from src.core.email import MagicLinkManager, EmailService, EmailSettings

                smtp_settings = EmailSettings.get_settings()
                if smtp_settings.get('smtp_enabled'):
                    # Create magic link
                    token = MagicLinkManager.create_magic_link(student_id, exam_id, 'exam_attempt')

                    if token:
                        success, message = EmailService.send_exam_assignment(
                            student_email=student['email'],
                            student_name=student['full_name'],
                            exam_title=question_set['title'],
                            subject_name=question_set['subject_name'],
                            exam_date=exam_date,
                            deadline=deadline if deadline else 'No deadline',
                            magic_link_token=token,
                            base_url=get_base_url()
                        )
                        email_sent = success

            AuditLogger.log_action(request.current_user['id'], 'exam_assigned',
                                  resource_type='practice_exam', resource_id=str(exam_id),
                                  details={'student_id': student_id, 'question_set_id': question_set_id, 'email_sent': email_sent},
                                  ip_address=get_client_ip())

            return jsonify({
                'success': True,
                'message': 'Exam assigned successfully' + (' (email sent)' if email_sent else ''),
                'id': exam_id,
                'email_sent': email_sent
            }), 200

        finally:
            cursor.close()
            conn.close()

    except Exception as e:
        print(f"Assign exam error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/question-sets')
@role_required('Admin')
def question_sets():
    """Manage question sets with pagination and search"""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 20))
    search = request.args.get('search', '').strip()
    subject_id = request.args.get('subject', '')

    try:
        # Get subjects
        cursor.execute("SELECT * FROM subjects WHERE is_active = TRUE ORDER BY name")
        subjects = cursor.fetchall()

        # Build query
        where_clauses = ["qs.is_active = TRUE"]
        params = []

        if search:
            where_clauses.append("qs.title LIKE %s")
            params.append(f'%{search}%')

        if subject_id:
            where_clauses.append("qs.subject_id = %s")
            params.append(subject_id)

        where_sql = " AND ".join(where_clauses)

        # Count
        cursor.execute(f"SELECT COUNT(*) as count FROM question_sets qs WHERE {where_sql}", params)
        total = cursor.fetchone()['count']

        paginator = Paginator(total, page, per_page)

        # Get question sets
        cursor.execute(f"""
            SELECT qs.*, s.name as subject_name, s.code as subject_code,
                   (SELECT COUNT(*) FROM questions WHERE question_set_id = qs.id AND is_active = TRUE) as question_count,
                   (SELECT COUNT(*) FROM practice_exams WHERE question_set_id = qs.id) as assigned_count
            FROM question_sets qs
            JOIN subjects s ON qs.subject_id = s.id
            WHERE {where_sql}
            ORDER BY s.name, qs.title
            LIMIT %s OFFSET %s
        """, params + [paginator.limit, paginator.offset])
        question_sets = cursor.fetchall()

        return render_template('admin/question_sets.html',
                             question_sets=question_sets,
                             subjects=subjects,
                             pagination=paginator.to_dict(),
                             search=search,
                             selected_subject=subject_id,
                             user=request.current_user)

    finally:
        cursor.close()
        conn.close()


@admin_bp.route('/question-sets/<int:set_id>')
@role_required('Admin')
def view_question_set(set_id):
    """View questions in a set"""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # Get question set
        cursor.execute("""
            SELECT qs.*, s.name as subject_name, s.code as subject_code
            FROM question_sets qs
            JOIN subjects s ON qs.subject_id = s.id
            WHERE qs.id = %s
        """, (set_id,))
        question_set = cursor.fetchone()

        if not question_set:
            return redirect(url_for('admin.question_sets'))

        # Get questions
        cursor.execute("""
            SELECT * FROM questions
            WHERE question_set_id = %s AND is_active = TRUE
            ORDER BY question_number
        """, (set_id,))
        questions = cursor.fetchall()

        for q in questions:
            if q['options']:
                q['options'] = json.loads(q['options']) if isinstance(q['options'], str) else q['options']

        return render_template('admin/view_questions.html',
                             question_set=question_set,
                             questions=questions,
                             user=request.current_user)

    finally:
        cursor.close()
        conn.close()


@admin_bp.route('/grading')
@role_required('Admin')
def grading():
    """Grade submitted exams with pagination"""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 20))
    status = request.args.get('status', 'pending')

    try:
        # Build query based on status
        if status == 'pending':
            status_filter = "pe.status IN ('submitted', 'grading')"
        elif status == 'released':
            status_filter = "pe.status = 'released'"
        else:
            status_filter = "1=1"

        # Count
        cursor.execute(f"""
            SELECT COUNT(*) as count FROM practice_exams pe WHERE {status_filter}
        """)
        total = cursor.fetchone()['count']

        paginator = Paginator(total, page, per_page)

        cursor.execute(f"""
            SELECT pe.*, u.full_name as student_name, qs.title as exam_title,
                   s.name as subject_name, s.code as subject_code
            FROM practice_exams pe
            JOIN users u ON pe.student_id = u.id
            JOIN question_sets qs ON pe.question_set_id = qs.id
            JOIN subjects s ON qs.subject_id = s.id
            WHERE {status_filter}
            ORDER BY pe.submitted_at DESC
            LIMIT %s OFFSET %s
        """, (paginator.limit, paginator.offset))
        exams = cursor.fetchall()

        for exam in exams:
            if exam['submitted_at']:
                exam['submitted_at'] = exam['submitted_at'].strftime('%d %b %Y %H:%M')
            if exam['exam_date']:
                exam['exam_date'] = exam['exam_date'].strftime('%d %b %Y')

        return render_template('admin/grading.html',
                             exams=exams,
                             pagination=paginator.to_dict(),
                             selected_status=status,
                             user=request.current_user)

    finally:
        cursor.close()
        conn.close()


@admin_bp.route('/grading/<int:exam_id>')
@role_required('Admin')
def grade_exam(exam_id):
    """Grade a specific exam"""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # Get exam info with sharing fields
        cursor.execute("""
            SELECT pe.*, u.full_name as student_name, qs.title as exam_title,
                   s.name as subject_name, pe.is_public, pe.share_token, pe.share_views
            FROM practice_exams pe
            JOIN users u ON pe.student_id = u.id
            JOIN question_sets qs ON pe.question_set_id = qs.id
            JOIN subjects s ON qs.subject_id = s.id
            WHERE pe.id = %s
        """, (exam_id,))
        exam = cursor.fetchone()

        if not exam:
            return redirect(url_for('admin.grading'))

        # Get questions with answers
        cursor.execute("""
            SELECT q.*, sa.student_answer, sa.drawing_data, sa.is_correct, sa.marks_awarded,
                   sa.admin_feedback, sa.auto_graded
            FROM questions q
            LEFT JOIN student_answers sa ON sa.question_id = q.id AND sa.practice_exam_id = %s
            WHERE q.question_set_id = %s
            ORDER BY q.question_number
        """, (exam_id, exam['question_set_id']))
        questions = cursor.fetchall()

        # Parse JSON fields
        for q in questions:
            if q['options']:
                q['options'] = json.loads(q['options']) if isinstance(q['options'], str) else q['options']
            if q['matching_pairs']:
                q['matching_pairs'] = json.loads(q['matching_pairs']) if isinstance(q['matching_pairs'], str) else q['matching_pairs']
            # For drawing questions, use drawing_data as the answer display
            if q['question_type'] == 'drawing' and q.get('drawing_data'):
                q['student_answer'] = q['drawing_data']

        if exam['exam_date']:
            exam['exam_date'] = exam['exam_date'].strftime('%d %b %Y')

        return render_template('admin/grade_exam.html',
                             exam=exam,
                             questions=questions,
                             user=request.current_user)

    finally:
        cursor.close()
        conn.close()


@admin_bp.route('/grading/<int:exam_id>/save', methods=['POST'])
@role_required('Admin')
def save_grades(exam_id):
    """Save grades for an exam"""
    try:
        data = request.get_json()
        grades = data.get('grades', [])

        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            total_score = 0

            for grade in grades:
                question_id = grade['question_id']
                marks_awarded = grade.get('marks_awarded', 0)
                feedback = grade.get('feedback', '')

                # Check if student answer exists
                cursor.execute("""
                    SELECT id, student_answer, is_correct, auto_graded
                    FROM student_answers
                    WHERE practice_exam_id = %s AND question_id = %s
                """, (exam_id, question_id))
                existing = cursor.fetchone()

                if existing:
                    # Update existing answer - preserve student_answer, is_correct, auto_graded
                    cursor.execute("""
                        UPDATE student_answers
                        SET marks_awarded = %s, admin_feedback = %s, graded_at = NOW()
                        WHERE practice_exam_id = %s AND question_id = %s
                    """, (marks_awarded, feedback, exam_id, question_id))
                else:
                    # Insert new record (for questions student didn't answer)
                    cursor.execute("""
                        INSERT INTO student_answers
                        (practice_exam_id, question_id, student_answer, marks_awarded, admin_feedback, graded_at)
                        VALUES (%s, %s, '', %s, %s, NOW())
                    """, (exam_id, question_id, marks_awarded, feedback))

                total_score += marks_awarded

            # Update exam status and score
            cursor.execute("""
                UPDATE practice_exams
                SET status = 'grading', total_score = %s, graded_by = %s, graded_at = NOW()
                WHERE id = %s
            """, (total_score, request.current_user['id'], exam_id))

            conn.commit()

            return jsonify({'success': True, 'message': 'Grades saved', 'total_score': total_score}), 200

        finally:
            cursor.close()
            conn.close()

    except Exception as e:
        print(f"Save grades error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/grading/<int:exam_id>/release', methods=['POST'])
@role_required('Admin')
def release_results(exam_id):
    """Release exam results to student with optional email notification"""
    try:
        data = request.get_json() or {}
        send_email = data.get('send_email', True)

        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            # Calculate final score
            cursor.execute("""
                SELECT COALESCE(SUM(marks_awarded), 0) as total FROM student_answers WHERE practice_exam_id = %s
            """, (exam_id,))
            result = cursor.fetchone()
            total_score = int(result['total']) if result['total'] else 0

            # Get exam and student info
            cursor.execute("""
                SELECT pe.*, u.email as student_email, u.full_name as student_name, qs.title as exam_title
                FROM practice_exams pe
                JOIN users u ON pe.student_id = u.id
                JOIN question_sets qs ON pe.question_set_id = qs.id
                WHERE pe.id = %s
            """, (exam_id,))
            exam = cursor.fetchone()
            max_score = exam['max_score'] if exam else 50

            percentage = (total_score / max_score * 100) if max_score > 0 else 0

            # Update exam
            cursor.execute("""
                UPDATE practice_exams
                SET status = 'released', total_score = %s, percentage = %s,
                    answers_released = TRUE, released_at = NOW()
                WHERE id = %s
            """, (total_score, percentage, exam_id))

            conn.commit()

            # Send email notification
            email_sent = False
            if send_email and exam['student_email']:
                from src.core.email import EmailService, EmailSettings

                smtp_settings = EmailSettings.get_settings()
                if smtp_settings.get('smtp_enabled'):
                    success, message = EmailService.send_results_released(
                        student_email=exam['student_email'],
                        student_name=exam['student_name'],
                        exam_title=exam['exam_title'],
                        score=total_score,
                        percentage=percentage,
                        base_url=get_base_url()
                    )
                    email_sent = success

            AuditLogger.log_action(request.current_user['id'], 'results_released',
                                  resource_type='practice_exam', resource_id=str(exam_id),
                                  details={'email_sent': email_sent},
                                  ip_address=get_client_ip())

            return jsonify({
                'success': True,
                'message': 'Results released' + (' (email sent)' if email_sent else ''),
                'total_score': total_score,
                'percentage': round(percentage, 1),
                'email_sent': email_sent
            }), 200

        finally:
            cursor.close()
            conn.close()

    except Exception as e:
        print(f"Release results error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/reports')
@role_required('Admin')
def reports():
    """View student reports with pagination"""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 20))

    try:
        # Count students
        cursor.execute("SELECT COUNT(*) as count FROM users WHERE role_id = 2 AND is_active = TRUE")
        total = cursor.fetchone()['count']

        paginator = Paginator(total, page, per_page)

        # Get performance by student
        cursor.execute("""
            SELECT u.id, u.full_name, u.email,
                   COUNT(pe.id) as total_exams,
                   AVG(pe.percentage) as avg_score,
                   MAX(pe.percentage) as best_score,
                   MIN(pe.percentage) as lowest_score
            FROM users u
            LEFT JOIN practice_exams pe ON pe.student_id = u.id AND pe.status = 'released'
            WHERE u.role_id = 2 AND u.is_active = TRUE
            GROUP BY u.id, u.full_name, u.email
            ORDER BY avg_score DESC
            LIMIT %s OFFSET %s
        """, (paginator.limit, paginator.offset))
        student_stats = cursor.fetchall()

        # Get performance by subject
        cursor.execute("""
            SELECT s.name as subject_name, s.code,
                   COUNT(pe.id) as total_exams,
                   AVG(pe.percentage) as avg_score
            FROM subjects s
            LEFT JOIN question_sets qs ON qs.subject_id = s.id
            LEFT JOIN practice_exams pe ON pe.question_set_id = qs.id AND pe.status = 'released'
            GROUP BY s.id, s.name, s.code
            ORDER BY s.name
        """)
        subject_stats = cursor.fetchall()

        return render_template('admin/reports.html',
                             student_stats=student_stats,
                             subject_stats=subject_stats,
                             pagination=paginator.to_dict(),
                             user=request.current_user)

    finally:
        cursor.close()
        conn.close()


@admin_bp.route('/audit-logs')
@role_required('Admin')
def audit_logs():
    """View audit logs with pagination and filters"""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 50))
    action = request.args.get('action', '')
    user_id = request.args.get('user_id', '')

    try:
        # Build query
        where_clauses = ["1=1"]
        params = []

        if action:
            where_clauses.append("al.action = %s")
            params.append(action)

        if user_id:
            where_clauses.append("al.user_id = %s")
            params.append(user_id)

        where_sql = " AND ".join(where_clauses)

        # Count
        cursor.execute(f"SELECT COUNT(*) as count FROM audit_logs al WHERE {where_sql}", params)
        total = cursor.fetchone()['count']

        paginator = Paginator(total, page, per_page)

        # Get logs
        cursor.execute(f"""
            SELECT al.*, u.full_name as user_name, u.email as user_email
            FROM audit_logs al
            LEFT JOIN users u ON al.user_id = u.id
            WHERE {where_sql}
            ORDER BY al.created_at DESC
            LIMIT %s OFFSET %s
        """, params + [paginator.limit, paginator.offset])
        logs = cursor.fetchall()

        for log in logs:
            if log['created_at']:
                log['created_at'] = log['created_at'].strftime('%d %b %Y %H:%M:%S')
            if log['details'] and isinstance(log['details'], str):
                try:
                    log['details'] = json.loads(log['details'])
                except:
                    pass

        # Get distinct actions for filter
        cursor.execute("SELECT DISTINCT action FROM audit_logs ORDER BY action")
        actions = [r['action'] for r in cursor.fetchall()]

        # Get users for filter
        cursor.execute("SELECT id, full_name FROM users ORDER BY full_name")
        users = cursor.fetchall()

        return render_template('admin/audit_logs.html',
                             logs=logs,
                             actions=actions,
                             users=users,
                             pagination=paginator.to_dict(),
                             selected_action=action,
                             selected_user=user_id,
                             user=request.current_user)

    finally:
        cursor.close()
        conn.close()


@admin_bp.route('/search')
@role_required('Admin')
def global_search():
    """Global search across students, exams, and questions"""
    query = request.args.get('q', '').strip()

    if not query or len(query) < 2:
        return jsonify({'results': [], 'message': 'Enter at least 2 characters'}), 200

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        results = {
            'students': [],
            'exams': [],
            'question_sets': []
        }

        # Search students
        cursor.execute("""
            SELECT id, full_name, email FROM users
            WHERE role_id = 2 AND (full_name LIKE %s OR email LIKE %s)
            LIMIT 5
        """, (f'%{query}%', f'%{query}%'))
        results['students'] = cursor.fetchall()

        # Search exams
        cursor.execute("""
            SELECT pe.id, qs.title as exam_title, u.full_name as student_name, pe.status
            FROM practice_exams pe
            JOIN question_sets qs ON pe.question_set_id = qs.id
            JOIN users u ON pe.student_id = u.id
            WHERE qs.title LIKE %s OR u.full_name LIKE %s
            LIMIT 5
        """, (f'%{query}%', f'%{query}%'))
        results['exams'] = cursor.fetchall()

        # Search question sets
        cursor.execute("""
            SELECT qs.id, qs.title, s.name as subject_name
            FROM question_sets qs
            JOIN subjects s ON qs.subject_id = s.id
            WHERE qs.title LIKE %s
            LIMIT 5
        """, (f'%{query}%',))
        results['question_sets'] = cursor.fetchall()

        return jsonify({'success': True, 'results': results}), 200

    finally:
        cursor.close()
        conn.close()


@admin_bp.route('/exams/<int:exam_id>/preview')
@role_required('Admin')
def exam_preview(exam_id):
    """Get exam details with questions for preview modal"""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # Get exam info
        cursor.execute("""
            SELECT pe.*, u.full_name as student_name, u.email as student_email,
                   qs.title as exam_title, qs.description as exam_description,
                   qs.duration_minutes, qs.difficulty,
                   s.name as subject_name, s.code as subject_code, s.color as subject_color
            FROM practice_exams pe
            JOIN users u ON pe.student_id = u.id
            JOIN question_sets qs ON pe.question_set_id = qs.id
            JOIN subjects s ON qs.subject_id = s.id
            WHERE pe.id = %s
        """, (exam_id,))
        exam = cursor.fetchone()

        if not exam:
            return jsonify({'success': False, 'error': 'Exam not found'}), 404

        # Keep raw date for edit form
        exam['exam_date_raw'] = exam['exam_date'].strftime('%Y-%m-%d') if exam['exam_date'] else ''

        # Get scheduled time if available
        if exam.get('scheduled_at'):
            exam['scheduled_time'] = exam['scheduled_at'].strftime('%H:%M')
            exam['scheduled_at'] = exam['scheduled_at'].strftime('%d %b %Y %H:%M')
        else:
            exam['scheduled_time'] = ''

        # Format dates for display
        if exam['exam_date']:
            exam['exam_date'] = exam['exam_date'].strftime('%d %b %Y')
        if exam['deadline']:
            exam['deadline'] = exam['deadline'].strftime('%d %b %Y %H:%M')
        if exam['created_at']:
            exam['created_at'] = exam['created_at'].strftime('%d %b %Y %H:%M')

        # Get questions
        cursor.execute("""
            SELECT id, question_number, question_type, question_text, marks,
                   options, image_url, hint
            FROM questions
            WHERE question_set_id = %s AND is_active = TRUE
            ORDER BY question_number
        """, (exam['question_set_id'],))
        questions = cursor.fetchall()

        # Parse JSON options
        for q in questions:
            if q['options']:
                try:
                    q['options'] = json.loads(q['options']) if isinstance(q['options'], str) else q['options']
                except:
                    q['options'] = []

        return jsonify({
            'success': True,
            'exam': exam,
            'questions': questions,
            'total_questions': len(questions),
            'total_marks': sum(q['marks'] for q in questions)
        }), 200

    finally:
        cursor.close()
        conn.close()


@admin_bp.route('/exams/<int:exam_id>/update-schedule', methods=['POST'])
@role_required('Admin')
def update_exam_schedule(exam_id):
    """Update exam schedule date and time"""
    try:
        data = request.get_json()
        exam_date = data.get('exam_date')
        exam_time = data.get('exam_time', '09:00')

        if not exam_date:
            return jsonify({'success': False, 'error': 'Date is required'}), 400

        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            # Verify exam exists and is pending
            cursor.execute("SELECT id, status FROM practice_exams WHERE id = %s", (exam_id,))
            exam = cursor.fetchone()

            if not exam:
                return jsonify({'success': False, 'error': 'Exam not found'}), 404

            if exam['status'] != 'pending':
                return jsonify({'success': False, 'error': 'Can only update schedule for pending exams'}), 400

            # Create scheduled_at datetime
            scheduled_at = f"{exam_date} {exam_time}:00"

            # Update exam
            cursor.execute("""
                UPDATE practice_exams
                SET exam_date = %s, scheduled_at = %s
                WHERE id = %s
            """, (exam_date, scheduled_at, exam_id))
            conn.commit()

            # Format for display
            from datetime import datetime
            scheduled_dt = datetime.strptime(scheduled_at, '%Y-%m-%d %H:%M:%S')
            scheduled_display = scheduled_dt.strftime('%d %b %Y %H:%M')

            return jsonify({
                'success': True,
                'scheduled_display': scheduled_display
            }), 200

        finally:
            cursor.close()
            conn.close()

    except Exception as e:
        print(f"Update schedule error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/exams/<int:exam_id>/reset', methods=['POST'])
@role_required('Admin')
def reset_exam(exam_id):
    """Reset an exam to allow student to retake it"""
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            # Get exam info
            cursor.execute("""
                SELECT pe.*, u.full_name as student_name, u.email as student_email, qs.title as exam_title
                FROM practice_exams pe
                JOIN users u ON pe.student_id = u.id
                JOIN question_sets qs ON pe.question_set_id = qs.id
                WHERE pe.id = %s
            """, (exam_id,))
            exam = cursor.fetchone()

            if not exam:
                return jsonify({'success': False, 'error': 'Exam not found'}), 404

            # Only allow reset for submitted, grading, or released exams
            if exam['status'] not in ('submitted', 'grading', 'released', 'in_progress'):
                return jsonify({'success': False, 'error': f'Cannot reset exam with status: {exam["status"]}'}), 400

            # Delete all student answers for this exam
            cursor.execute("DELETE FROM student_answers WHERE practice_exam_id = %s", (exam_id,))

            # Reset the exam to pending status
            cursor.execute("""
                UPDATE practice_exams
                SET status = 'pending',
                    started_at = NULL,
                    submitted_at = NULL,
                    total_score = NULL,
                    percentage = NULL,
                    graded_by = NULL,
                    graded_at = NULL,
                    answers_released = FALSE,
                    released_at = NULL
                WHERE id = %s
            """, (exam_id,))

            conn.commit()

            AuditLogger.log_action(request.current_user['id'], 'exam_reset',
                                  resource_type='practice_exam', resource_id=str(exam_id),
                                  details={
                                      'student_id': exam['student_id'],
                                      'student_name': exam['student_name'],
                                      'exam_title': exam['exam_title'],
                                      'previous_status': exam['status']
                                  },
                                  ip_address=get_client_ip())

            return jsonify({
                'success': True,
                'message': f'Exam reset for {exam["student_name"]}. Student can now retake the exam.'
            }), 200

        finally:
            cursor.close()
            conn.close()

    except Exception as e:
        print(f"Reset exam error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/exams/filter')
@role_required('Admin')
def exams_filter():
    """Filter exams with multiple criteria - AJAX endpoint"""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # Get filter params
        subject_id = request.args.get('subject', '')
        student_id = request.args.get('student', '')
        status = request.args.get('status', '')
        date_from = request.args.get('date_from', '')
        date_to = request.args.get('date_to', '')
        search = request.args.get('search', '').strip()

        # Build query
        where_clauses = ["1=1"]
        params = []

        if subject_id:
            where_clauses.append("qs.subject_id = %s")
            params.append(subject_id)

        if student_id:
            where_clauses.append("pe.student_id = %s")
            params.append(student_id)

        if status:
            where_clauses.append("pe.status = %s")
            params.append(status)

        if date_from:
            where_clauses.append("pe.exam_date >= %s")
            params.append(date_from)

        if date_to:
            where_clauses.append("pe.exam_date <= %s")
            params.append(date_to)

        if search:
            where_clauses.append("(qs.title LIKE %s OR u.full_name LIKE %s)")
            params.extend([f'%{search}%', f'%{search}%'])

        where_sql = " AND ".join(where_clauses)

        # Get filtered exams
        cursor.execute(f"""
            SELECT pe.id, pe.status, pe.exam_date, pe.deadline, pe.scheduled_at,
                   u.full_name as student_name, u.id as student_id,
                   qs.title as exam_title, qs.id as question_set_id,
                   s.name as subject_name, s.code as subject_code, s.id as subject_id
            FROM practice_exams pe
            JOIN users u ON pe.student_id = u.id
            JOIN question_sets qs ON pe.question_set_id = qs.id
            JOIN subjects s ON qs.subject_id = s.id
            WHERE {where_sql}
            ORDER BY pe.created_at DESC
            LIMIT 100
        """, params)
        exams = cursor.fetchall()

        # Format dates and calculate display status
        now = datetime.now()
        for exam in exams:
            # Calculate display status for pending exams
            exam['display_status'] = exam['status']
            if exam['status'] == 'pending' and exam.get('scheduled_at'):
                scheduled = exam['scheduled_at']
                if scheduled > now:
                    time_until = (scheduled - now).total_seconds()
                    if time_until <= 3600:  # Within 1 hour
                        exam['display_status'] = 'soon'
                    else:
                        exam['display_status'] = 'scheduled'

            # Format dates for JSON
            if exam['exam_date']:
                exam['exam_date'] = exam['exam_date'].strftime('%d %b %Y')
            if exam['scheduled_at']:
                exam['scheduled_time'] = exam['scheduled_at'].strftime('%H:%M')
                exam['scheduled_at'] = exam['scheduled_at'].strftime('%d %b %Y %H:%M')
            if exam['deadline']:
                exam['deadline'] = exam['deadline'].strftime('%d %b %Y %H:%M')

        return jsonify({
            'success': True,
            'exams': exams,
            'count': len(exams)
        }), 200

    finally:
        cursor.close()
        conn.close()
