"""
Y6 Practice Exam - Public Sharing Routes
Public URL access for questions and exam results
"""

from flask import Blueprint, request, jsonify, render_template, abort
from datetime import datetime
import json
import secrets
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src" / "core"))
sys.path.insert(0, str(PROJECT_ROOT / "dbs"))

from src.core.auth import login_required, AuditLogger
from dbs.connection import get_connection

public_bp = Blueprint('public', __name__, url_prefix='/share')


def generate_share_token():
    """Generate a unique share token"""
    return secrets.token_urlsafe(16)


@public_bp.route('/exam/<token>')
def view_shared_exam(token):
    """View a publicly shared exam result"""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # Get shared exam
        cursor.execute("""
            SELECT pe.*, qs.title as exam_title, s.name as subject_name,
                   u.full_name as student_name, pe.share_token
            FROM practice_exams pe
            JOIN question_sets qs ON pe.question_set_id = qs.id
            JOIN subjects s ON qs.subject_id = s.id
            JOIN users u ON pe.student_id = u.id
            WHERE pe.share_token = %s AND pe.is_public = TRUE
        """, (token,))
        exam = cursor.fetchone()

        if not exam:
            abort(404)

        # Only show released exams
        if exam['status'] != 'released':
            abort(404)

        # Get questions and answers
        cursor.execute("""
            SELECT q.*, sa.student_answer, sa.is_correct, sa.marks_awarded
            FROM questions q
            LEFT JOIN student_answers sa ON sa.question_id = q.id AND sa.practice_exam_id = %s
            WHERE q.question_set_id = %s AND q.is_active = TRUE
            ORDER BY q.question_number
        """, (exam['id'], exam['question_set_id']))
        questions = cursor.fetchall()

        # Parse JSON fields
        for q in questions:
            if q['options']:
                q['options'] = json.loads(q['options']) if isinstance(q['options'], str) else q['options']

        # Increment view count
        cursor.execute("""
            UPDATE practice_exams SET share_views = COALESCE(share_views, 0) + 1 WHERE id = %s
        """, (exam['id'],))
        conn.commit()

        return render_template('public/shared_exam.html',
                             exam=exam,
                             questions=questions,
                             is_public=True)

    finally:
        cursor.close()
        conn.close()


@public_bp.route('/question/<token>')
def view_shared_question(token):
    """View a publicly shared question set"""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # Get shared question set
        cursor.execute("""
            SELECT qs.*, s.name as subject_name, s.code as subject_code
            FROM question_sets qs
            JOIN subjects s ON qs.subject_id = s.id
            WHERE qs.share_token = %s AND qs.is_public = TRUE
        """, (token,))
        question_set = cursor.fetchone()

        if not question_set:
            abort(404)

        # Get questions (without answers for public view)
        cursor.execute("""
            SELECT id, question_number, question_type, question_text,
                   question_html, image_url, marks, options, hint
            FROM questions
            WHERE question_set_id = %s AND is_active = TRUE
            ORDER BY question_number
        """, (question_set['id'],))
        questions = cursor.fetchall()

        # Parse JSON fields
        for q in questions:
            if q['options']:
                q['options'] = json.loads(q['options']) if isinstance(q['options'], str) else q['options']

        # Increment view count
        cursor.execute("""
            UPDATE question_sets SET share_views = COALESCE(share_views, 0) + 1 WHERE id = %s
        """, (question_set['id'],))
        conn.commit()

        return render_template('public/shared_questions.html',
                             question_set=question_set,
                             questions=questions,
                             is_public=True)

    finally:
        cursor.close()
        conn.close()


@public_bp.route('/create', methods=['POST'])
@login_required
def create_share_link():
    """Create a public share link for exam or question set"""
    try:
        data = request.get_json()
        share_type = data.get('type')  # 'exam' or 'question_set'
        item_id = data.get('id')

        if not share_type or not item_id:
            return jsonify({'success': False, 'error': 'Invalid request'}), 400

        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            token = generate_share_token()

            if share_type == 'exam':
                # Verify ownership or admin
                cursor.execute("""
                    SELECT * FROM practice_exams WHERE id = %s
                """, (item_id,))
                exam = cursor.fetchone()

                if not exam:
                    return jsonify({'success': False, 'error': 'Exam not found'}), 404

                # Check permission (student owns exam or admin)
                user = request.current_user
                if user['role_name'] != 'Admin' and exam['student_id'] != user['id']:
                    return jsonify({'success': False, 'error': 'Permission denied'}), 403

                # Update exam with share token
                cursor.execute("""
                    UPDATE practice_exams
                    SET is_public = TRUE, share_token = %s, shared_at = NOW(), shared_by = %s
                    WHERE id = %s
                """, (token, user['id'], item_id))

            elif share_type == 'question_set':
                # Only admin can share question sets
                if request.current_user['role_name'] != 'Admin':
                    return jsonify({'success': False, 'error': 'Admin only'}), 403

                cursor.execute("""
                    UPDATE question_sets
                    SET is_public = TRUE, share_token = %s, shared_at = NOW()
                    WHERE id = %s
                """, (token, item_id))

            else:
                return jsonify({'success': False, 'error': 'Invalid share type'}), 400

            conn.commit()

            share_url = f"/share/{share_type.replace('_', '-')}/{token}"

            AuditLogger.log_action(request.current_user['id'], 'share_created',
                                  resource_type=share_type, resource_id=str(item_id),
                                  details={'token': token},
                                  ip_address=request.remote_addr)

            return jsonify({
                'success': True,
                'token': token,
                'share_url': share_url,
                'message': 'Share link created successfully'
            }), 200

        finally:
            cursor.close()
            conn.close()

    except Exception as e:
        print(f"Create share error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@public_bp.route('/revoke', methods=['POST'])
@login_required
def revoke_share():
    """Revoke a public share link"""
    try:
        data = request.get_json()
        share_type = data.get('type')
        item_id = data.get('id')

        if not share_type or not item_id:
            return jsonify({'success': False, 'error': 'Invalid request'}), 400

        conn = get_connection()
        cursor = conn.cursor()

        try:
            if share_type == 'exam':
                cursor.execute("""
                    UPDATE practice_exams
                    SET is_public = FALSE, share_token = NULL
                    WHERE id = %s
                """, (item_id,))

            elif share_type == 'question_set':
                cursor.execute("""
                    UPDATE question_sets
                    SET is_public = FALSE, share_token = NULL
                    WHERE id = %s
                """, (item_id,))

            conn.commit()

            AuditLogger.log_action(request.current_user['id'], 'share_revoked',
                                  resource_type=share_type, resource_id=str(item_id),
                                  ip_address=request.remote_addr)

            return jsonify({'success': True, 'message': 'Share link revoked'}), 200

        finally:
            cursor.close()
            conn.close()

    except Exception as e:
        print(f"Revoke share error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
