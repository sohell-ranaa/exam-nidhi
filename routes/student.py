"""
Y6 Practice Exam - Student Routes
Dashboard, take exam, view results
"""

from flask import Blueprint, request, jsonify, render_template, redirect, url_for
from datetime import datetime, timedelta
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src" / "core"))
sys.path.insert(0, str(PROJECT_ROOT / "dbs"))

from src.core.auth import login_required, role_required, AuditLogger
from dbs.connection import get_connection

student_bp = Blueprint('student', __name__, url_prefix='/student')


@student_bp.route('/')
@student_bp.route('/dashboard')
@role_required('Student')
def dashboard():
    """Student dashboard"""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    student_id = request.current_user['id']

    try:
        # Get pending exams
        cursor.execute("""
            SELECT pe.*, qs.title as exam_title, s.name as subject_name, s.code as subject_code
            FROM practice_exams pe
            JOIN question_sets qs ON pe.question_set_id = qs.id
            JOIN subjects s ON qs.subject_id = s.id
            WHERE pe.student_id = %s AND pe.status IN ('pending', 'in_progress')
            ORDER BY pe.exam_date ASC
        """, (student_id,))
        pending_exams = cursor.fetchall()

        # Get completed exams
        cursor.execute("""
            SELECT pe.*, qs.title as exam_title, s.name as subject_name, s.code as subject_code
            FROM practice_exams pe
            JOIN question_sets qs ON pe.question_set_id = qs.id
            JOIN subjects s ON qs.subject_id = s.id
            WHERE pe.student_id = %s AND pe.status = 'released'
            ORDER BY pe.released_at DESC
            LIMIT 10
        """, (student_id,))
        completed_exams = cursor.fetchall()

        # Get overall stats
        cursor.execute("""
            SELECT COUNT(*) as total_exams,
                   AVG(percentage) as avg_score,
                   MAX(percentage) as best_score
            FROM practice_exams
            WHERE student_id = %s AND status = 'released'
        """, (student_id,))
        stats = cursor.fetchone()

        # Format dates
        for exam in pending_exams:
            if exam['exam_date']:
                exam['exam_date'] = exam['exam_date'].strftime('%d %b %Y')

        for exam in completed_exams:
            if exam['released_at']:
                exam['released_at'] = exam['released_at'].strftime('%d %b %Y')

        return render_template('student/dashboard.html',
                             pending_exams=pending_exams,
                             completed_exams=completed_exams,
                             stats=stats,
                             user=request.current_user)

    finally:
        cursor.close()
        conn.close()


@student_bp.route('/exam/<int:exam_id>')
@role_required('Student')
def take_exam(exam_id):
    """Take an exam"""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    student_id = request.current_user['id']

    try:
        # Get exam info
        cursor.execute("""
            SELECT pe.*, qs.title as exam_title, qs.duration_minutes,
                   s.name as subject_name, s.code as subject_code
            FROM practice_exams pe
            JOIN question_sets qs ON pe.question_set_id = qs.id
            JOIN subjects s ON qs.subject_id = s.id
            WHERE pe.id = %s AND pe.student_id = %s
        """, (exam_id, student_id))
        exam = cursor.fetchone()

        if not exam:
            return redirect(url_for('student.dashboard'))

        # Check if already submitted or released
        if exam['status'] in ('submitted', 'grading', 'released'):
            return redirect(url_for('student.view_results', exam_id=exam_id))

        # Start exam if pending - set started_at to NOW
        if exam['status'] == 'pending':
            cursor.execute("""
                UPDATE practice_exams
                SET status = 'in_progress', started_at = NOW()
                WHERE id = %s
            """, (exam_id,))
            conn.commit()
            # Refetch exam to get the updated started_at
            cursor.execute("""
                SELECT pe.*, qs.title as exam_title, qs.duration_minutes,
                       s.name as subject_name, s.code as subject_code
                FROM practice_exams pe
                JOIN question_sets qs ON pe.question_set_id = qs.id
                JOIN subjects s ON qs.subject_id = s.id
                WHERE pe.id = %s AND pe.student_id = %s
            """, (exam_id, student_id))
            exam = cursor.fetchone()

        # Get questions
        cursor.execute("""
            SELECT q.id, q.question_number, q.question_type, q.question_text,
                   q.question_html, q.image_url, q.marks, q.options, q.hint,
                   q.matching_pairs, q.drawing_template,
                   sa.student_answer, sa.drawing_data
            FROM questions q
            LEFT JOIN student_answers sa ON sa.question_id = q.id AND sa.practice_exam_id = %s
            WHERE q.question_set_id = %s AND q.is_active = TRUE
            ORDER BY q.question_number
        """, (exam_id, exam['question_set_id']))
        questions = cursor.fetchall()

        # Parse JSON fields
        for q in questions:
            if q['options']:
                q['options'] = json.loads(q['options']) if isinstance(q['options'], str) else q['options']
            if q['matching_pairs']:
                q['matching_pairs'] = json.loads(q['matching_pairs']) if isinstance(q['matching_pairs'], str) else q['matching_pairs']
            if q['drawing_template']:
                q['drawing_template'] = json.loads(q['drawing_template']) if isinstance(q['drawing_template'], str) else q['drawing_template']
            # Use drawing_data if available, otherwise use student_answer for drawing questions
            if q['question_type'] == 'drawing' and q.get('drawing_data'):
                q['student_answer'] = q['drawing_data']

        # Calculate max score
        max_score = sum(q['marks'] or 0 for q in questions)
        exam['max_score'] = max_score

        # Get current time right before rendering
        current_time = datetime.now()

        # Debug: Log timer info to server console
        if exam.get('started_at'):
            duration = exam.get('duration_minutes') or 60
            elapsed = (current_time - exam['started_at']).total_seconds()
            remaining = (duration * 60) - elapsed
            print(f"[TIMER DEBUG] Exam {exam_id}: started={exam['started_at']}, now={current_time}, duration={duration}min, elapsed={elapsed:.0f}s, remaining={remaining:.0f}s")

        return render_template('student/take_exam.html',
                             exam=exam,
                             questions=questions,
                             now=current_time,
                             user=request.current_user)

    finally:
        cursor.close()
        conn.close()


@student_bp.route('/exam/<int:exam_id>/save', methods=['POST'])
@role_required('Student')
def save_answer(exam_id):
    """Save a single answer (auto-save)"""
    try:
        data = request.get_json()
        question_id = data.get('question_id')
        answer = data.get('answer', '')

        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            # Check if this is a drawing question
            cursor.execute("SELECT question_type FROM questions WHERE id = %s", (question_id,))
            question = cursor.fetchone()

            is_drawing = question and question['question_type'] == 'drawing'

            if is_drawing and answer and answer.startswith('data:image'):
                # Store drawing data in the drawing_data column
                cursor.execute("""
                    INSERT INTO student_answers (practice_exam_id, question_id, student_answer, drawing_data, answered_at)
                    VALUES (%s, %s, '', %s, NOW())
                    ON DUPLICATE KEY UPDATE drawing_data = %s, answered_at = NOW()
                """, (exam_id, question_id, answer, answer))
            else:
                # Regular answer
                cursor.execute("""
                    INSERT INTO student_answers (practice_exam_id, question_id, student_answer, answered_at)
                    VALUES (%s, %s, %s, NOW())
                    ON DUPLICATE KEY UPDATE student_answer = %s, answered_at = NOW()
                """, (exam_id, question_id, answer, answer))

            conn.commit()

            return jsonify({'success': True}), 200

        finally:
            cursor.close()
            conn.close()

    except Exception as e:
        print(f"Save answer error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@student_bp.route('/exam/<int:exam_id>/submit', methods=['POST'])
@role_required('Student')
def submit_exam(exam_id):
    """Submit exam for grading"""
    try:
        data = request.get_json()
        answers = data.get('answers', [])

        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        student_id = request.current_user['id']

        try:
            # Verify exam belongs to student
            cursor.execute("""
                SELECT pe.*, qs.id as qs_id FROM practice_exams pe
                JOIN question_sets qs ON pe.question_set_id = qs.id
                WHERE pe.id = %s AND pe.student_id = %s
            """, (exam_id, student_id))
            exam = cursor.fetchone()

            if not exam:
                return jsonify({'success': False, 'error': 'Exam not found'}), 404

            # Save all answers
            auto_graded_score = 0

            for ans in answers:
                question_id = ans['question_id']
                student_answer = ans.get('answer', '')

                # Get question info for auto-grading
                cursor.execute("""
                    SELECT question_type, correct_answer, marks FROM questions WHERE id = %s
                """, (question_id,))
                question = cursor.fetchone()

                is_correct = None
                marks_awarded = None
                auto_graded = False
                drawing_data = None

                # Check if this is a drawing answer
                is_drawing = question and question['question_type'] == 'drawing'
                if is_drawing and student_answer and student_answer.startswith('data:image'):
                    drawing_data = student_answer
                    student_answer = ''  # Don't store base64 in student_answer column

                # Auto-grade MCQ and fill_blank
                if question and question['question_type'] in ('mcq', 'fill_blank'):
                    correct = question['correct_answer'].strip().lower()
                    given = str(student_answer).strip().lower()
                    is_correct = (correct == given)
                    marks_awarded = question['marks'] if is_correct else 0
                    auto_graded = True
                    auto_graded_score += marks_awarded

                # Upsert answer
                if drawing_data:
                    cursor.execute("""
                        INSERT INTO student_answers
                        (practice_exam_id, question_id, student_answer, drawing_data, is_correct, marks_awarded, auto_graded, answered_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
                        ON DUPLICATE KEY UPDATE
                        student_answer = %s, drawing_data = %s, is_correct = %s, marks_awarded = %s, auto_graded = %s, answered_at = NOW()
                    """, (exam_id, question_id, student_answer, drawing_data, is_correct, marks_awarded, auto_graded,
                          student_answer, drawing_data, is_correct, marks_awarded, auto_graded))
                else:
                    cursor.execute("""
                        INSERT INTO student_answers
                        (practice_exam_id, question_id, student_answer, is_correct, marks_awarded, auto_graded, answered_at)
                        VALUES (%s, %s, %s, %s, %s, %s, NOW())
                        ON DUPLICATE KEY UPDATE
                        student_answer = %s, is_correct = %s, marks_awarded = %s, auto_graded = %s, answered_at = NOW()
                    """, (exam_id, question_id, student_answer, is_correct, marks_awarded, auto_graded,
                          student_answer, is_correct, marks_awarded, auto_graded))

            # Check if submission is delayed (more than 60 minutes from started_at)
            is_delayed = False
            if exam.get('started_at'):
                elapsed_minutes = (datetime.now() - exam['started_at']).total_seconds() / 60
                is_delayed = elapsed_minutes > 60  # More than 60 minutes = delayed

            # Update exam status
            cursor.execute("""
                UPDATE practice_exams
                SET status = 'submitted', submitted_at = NOW(), auto_graded_score = %s, is_delayed = %s
                WHERE id = %s
            """, (auto_graded_score, is_delayed, exam_id))

            conn.commit()

            AuditLogger.log_action(student_id, 'exam_submitted',
                                  resource_type='practice_exam', resource_id=str(exam_id),
                                  details={'is_delayed': is_delayed},
                                  ip_address=request.remote_addr)

            message = 'Exam submitted successfully'
            if is_delayed:
                message = 'Exam submitted (marked as delayed - submitted after 60 minutes)'

            return jsonify({
                'success': True,
                'message': message,
                'auto_graded_score': auto_graded_score,
                'is_delayed': is_delayed
            }), 200

        finally:
            cursor.close()
            conn.close()

    except Exception as e:
        print(f"Submit exam error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@student_bp.route('/results/<int:exam_id>')
@role_required('Student')
def view_results(exam_id):
    """View exam results"""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    student_id = request.current_user['id']

    try:
        # Get exam info with sharing fields
        cursor.execute("""
            SELECT pe.*, qs.title as exam_title, s.name as subject_name,
                   pe.is_public, pe.share_token, pe.share_views
            FROM practice_exams pe
            JOIN question_sets qs ON pe.question_set_id = qs.id
            JOIN subjects s ON qs.subject_id = s.id
            WHERE pe.id = %s AND pe.student_id = %s
        """, (exam_id, student_id))
        exam = cursor.fetchone()

        if not exam:
            return redirect(url_for('student.dashboard'))

        # Check if results are released
        if not exam['answers_released']:
            return render_template('student/waiting.html', exam=exam, user=request.current_user)

        # Get questions with answers
        cursor.execute("""
            SELECT q.*, sa.student_answer, sa.is_correct, sa.marks_awarded, sa.admin_feedback
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

        return render_template('student/results.html',
                             exam=exam,
                             questions=questions,
                             user=request.current_user)

    finally:
        cursor.close()
        conn.close()


@student_bp.route('/my-exams')
@role_required('Student')
def my_exams():
    """View all exams with filters"""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    student_id = request.current_user['id']

    # Get filter params
    subject = request.args.get('subject', '')
    status = request.args.get('status', '')
    date_from = request.args.get('from', '')
    date_to = request.args.get('to', '')

    try:
        # Get subjects for filter dropdown
        cursor.execute("SELECT code, name FROM subjects ORDER BY name")
        subjects = cursor.fetchall()

        # Build query with filters
        query = """
            SELECT pe.*, pe.scheduled_at, qs.title as exam_title, s.name as subject_name, s.code as subject_code
            FROM practice_exams pe
            JOIN question_sets qs ON pe.question_set_id = qs.id
            JOIN subjects s ON qs.subject_id = s.id
            WHERE pe.student_id = %s
        """
        params = [student_id]

        if subject:
            query += " AND s.code = %s"
            params.append(subject)

        if status:
            if status == 'pending':
                query += " AND pe.status IN ('pending', 'in_progress')"
            elif status == 'completed':
                query += " AND pe.status IN ('submitted', 'grading', 'released')"
            elif status == 'released':
                query += " AND pe.status = 'released'"

        if date_from:
            query += " AND pe.exam_date >= %s"
            params.append(date_from)

        if date_to:
            query += " AND pe.exam_date <= %s"
            params.append(date_to)

        query += " ORDER BY pe.exam_date DESC"

        cursor.execute(query, params)
        exams = cursor.fetchall()

        now = datetime.now()
        for exam in exams:
            if exam['exam_date']:
                exam['exam_date_formatted'] = exam['exam_date'].strftime('%d %b %Y')
            if exam['submitted_at']:
                exam['submitted_at_formatted'] = exam['submitted_at'].strftime('%d %b %Y %H:%M')

            # Format scheduled time and check if it's in the future
            if exam.get('scheduled_at'):
                exam['scheduled_time_formatted'] = exam['scheduled_at'].strftime('%H:%M')
                exam['is_future'] = exam['scheduled_at'] > now
                # Calculate time until exam
                if exam['is_future']:
                    time_until = (exam['scheduled_at'] - now).total_seconds()
                    exam['is_soon'] = time_until <= 3600  # Within 1 hour
                else:
                    exam['is_soon'] = False
            else:
                exam['scheduled_time_formatted'] = None
                exam['is_future'] = False
                exam['is_soon'] = False

        return render_template('student/my_exams.html',
                             exams=exams,
                             subjects=subjects,
                             filters={'subject': subject, 'status': status, 'from': date_from, 'to': date_to},
                             user=request.current_user)

    finally:
        cursor.close()
        conn.close()


@student_bp.route('/results')
@role_required('Student')
def results():
    """View all released results"""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    student_id = request.current_user['id']

    subject = request.args.get('subject', '')

    try:
        # Get subjects for filter
        cursor.execute("SELECT code, name FROM subjects ORDER BY name")
        subjects = cursor.fetchall()

        # Get released exams
        query = """
            SELECT pe.*, qs.title as exam_title, s.name as subject_name, s.code as subject_code
            FROM practice_exams pe
            JOIN question_sets qs ON pe.question_set_id = qs.id
            JOIN subjects s ON qs.subject_id = s.id
            WHERE pe.student_id = %s AND pe.status = 'released'
        """
        params = [student_id]

        if subject:
            query += " AND s.code = %s"
            params.append(subject)

        query += " ORDER BY pe.released_at DESC"

        cursor.execute(query, params)
        exams = cursor.fetchall()

        for exam in exams:
            if exam['released_at']:
                exam['released_at_formatted'] = exam['released_at'].strftime('%d %b %Y')

        return render_template('student/results_list.html',
                             exams=exams,
                             subjects=subjects,
                             current_subject=subject,
                             user=request.current_user)

    finally:
        cursor.close()
        conn.close()


@student_bp.route('/history')
@role_required('Student')
def history():
    """View exam history - redirect to my-exams"""
    return redirect(url_for('student.my_exams'))
