"""
Y6 Practice Exam - Question Bank Routes
Subject-wise question pools with preview, download, and PDF export
"""

from flask import Blueprint, request, jsonify, render_template, Response, make_response
from datetime import datetime
import json
import io
import csv
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src" / "core"))
sys.path.insert(0, str(PROJECT_ROOT / "dbs"))

from src.core.auth import role_required, AuditLogger
from src.core.pagination import Paginator
from dbs.connection import get_connection

questions_bp = Blueprint('questions', __name__, url_prefix='/questions')


@questions_bp.route('/')
@questions_bp.route('/bank')
@role_required('Admin')
def question_bank():
    """
    Hierarchical question bank with three levels:
    - Level 1 (no params): Show all subjects with set counts and question counts
    - Level 2 (subject param): Show all question sets for that subject
    - Level 3 (subject + set params): Show all questions in that set
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    subject_param = request.args.get('subject', '')
    set_param = request.args.get('set', '')

    try:
        # Always get all subjects with counts
        cursor.execute("""
            SELECT s.*,
                   (SELECT COUNT(DISTINCT qs.id)
                    FROM question_sets qs
                    WHERE qs.subject_id = s.id AND qs.is_active = TRUE) as set_count,
                   (SELECT COUNT(*) FROM questions q
                    JOIN question_sets qs ON q.question_set_id = qs.id
                    WHERE qs.subject_id = s.id AND q.is_active = TRUE) as question_count
            FROM subjects s
            WHERE s.is_active = TRUE
            ORDER BY s.name
        """)
        subjects = cursor.fetchall()

        current_subject = None
        question_sets = None
        current_set = None
        questions = None

        # Level 2 or 3: Subject selected
        if subject_param:
            # Get current subject details
            cursor.execute("SELECT * FROM subjects WHERE code = %s AND is_active = TRUE", (subject_param,))
            current_subject = cursor.fetchone()

            if current_subject:
                # Get question sets for this subject with question counts
                cursor.execute("""
                    SELECT qs.*,
                           (SELECT COUNT(*) FROM questions
                            WHERE question_set_id = qs.id AND is_active = TRUE) as question_count
                    FROM question_sets qs
                    WHERE qs.subject_id = %s AND qs.is_active = TRUE
                    ORDER BY qs.title
                """, (current_subject['id'],))
                question_sets = cursor.fetchall()

                # Level 3: Set also selected
                if set_param:
                    try:
                        set_id = int(set_param)

                        # Get current set details
                        cursor.execute("""
                            SELECT * FROM question_sets
                            WHERE id = %s AND subject_id = %s AND is_active = TRUE
                        """, (set_id, current_subject['id']))
                        current_set = cursor.fetchone()

                        if current_set:
                            # Get all questions in this set
                            cursor.execute("""
                                SELECT * FROM questions
                                WHERE question_set_id = %s AND is_active = TRUE
                                ORDER BY question_number
                            """, (set_id,))
                            questions = cursor.fetchall()

                            # Parse JSON options for each question
                            for q in questions:
                                if q['options']:
                                    try:
                                        q['options'] = json.loads(q['options']) if isinstance(q['options'], str) else q['options']
                                    except:
                                        q['options'] = []
                    except (ValueError, TypeError):
                        pass  # Invalid set_id, ignore

        return render_template('admin/question_bank.html',
                             subjects=subjects,
                             current_subject=current_subject,
                             question_sets=question_sets,
                             current_set=current_set,
                             questions=questions,
                             user=request.current_user)

    finally:
        cursor.close()
        conn.close()


@questions_bp.route('/<int:question_id>')
@role_required('Admin')
def get_question(question_id):
    """Get single question details for preview"""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT q.*, qs.title as set_title, s.name as subject_name, s.code as subject_code
            FROM questions q
            JOIN question_sets qs ON q.question_set_id = qs.id
            JOIN subjects s ON qs.subject_id = s.id
            WHERE q.id = %s
        """, (question_id,))
        question = cursor.fetchone()

        if not question:
            return jsonify({'success': False, 'error': 'Question not found'}), 404

        if question['options']:
            try:
                question['options'] = json.loads(question['options']) if isinstance(question['options'], str) else question['options']
            except:
                question['options'] = []

        return jsonify({'success': True, 'question': question})

    finally:
        cursor.close()
        conn.close()


@questions_bp.route('/set/<int:set_id>')
@role_required('Admin')
def get_question_set(set_id):
    """Get all questions in a set for preview"""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # Get question set info
        cursor.execute("""
            SELECT qs.*, s.name as subject_name, s.code as subject_code
            FROM question_sets qs
            JOIN subjects s ON qs.subject_id = s.id
            WHERE qs.id = %s
        """, (set_id,))
        question_set = cursor.fetchone()

        if not question_set:
            return jsonify({'success': False, 'error': 'Question set not found'}), 404

        # Get questions
        cursor.execute("""
            SELECT * FROM questions
            WHERE question_set_id = %s AND is_active = TRUE
            ORDER BY question_number
        """, (set_id,))
        questions = cursor.fetchall()

        for q in questions:
            if q['options']:
                try:
                    q['options'] = json.loads(q['options']) if isinstance(q['options'], str) else q['options']
                except:
                    q['options'] = []

        return jsonify({
            'success': True,
            'question_set': question_set,
            'questions': questions
        })

    finally:
        cursor.close()
        conn.close()


@questions_bp.route('/export/json/<int:set_id>')
@role_required('Admin')
def export_json(set_id):
    """Export question set as JSON"""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT qs.*, s.name as subject_name
            FROM question_sets qs
            JOIN subjects s ON qs.subject_id = s.id
            WHERE qs.id = %s
        """, (set_id,))
        question_set = cursor.fetchone()

        if not question_set:
            return jsonify({'error': 'Not found'}), 404

        cursor.execute("""
            SELECT id, question_number, question_type, question_text, marks, options, correct_answer, hint
            FROM questions
            WHERE question_set_id = %s AND is_active = TRUE
            ORDER BY question_number
        """, (set_id,))
        questions = cursor.fetchall()

        for q in questions:
            if q['options']:
                try:
                    q['options'] = json.loads(q['options']) if isinstance(q['options'], str) else q['options']
                except:
                    q['options'] = []

        export_data = {
            'title': question_set['title'],
            'subject': question_set['subject_name'],
            'total_marks': question_set['total_marks'],
            'duration_minutes': question_set['duration_minutes'],
            'questions': questions,
            'exported_at': datetime.now().isoformat()
        }

        response = make_response(json.dumps(export_data, indent=2, default=str))
        response.headers['Content-Type'] = 'application/json'
        response.headers['Content-Disposition'] = f'attachment; filename="{question_set["title"].replace(" ", "_")}.json"'

        AuditLogger.log_action(request.current_user['id'], 'export_questions_json',
                              resource_type='question_set', resource_id=str(set_id),
                              ip_address=request.remote_addr)

        return response

    finally:
        cursor.close()
        conn.close()


@questions_bp.route('/export/csv/<int:set_id>')
@role_required('Admin')
def export_csv(set_id):
    """Export question set as CSV"""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT qs.title FROM question_sets qs WHERE qs.id = %s
        """, (set_id,))
        question_set = cursor.fetchone()

        if not question_set:
            return jsonify({'error': 'Not found'}), 404

        cursor.execute("""
            SELECT question_number, question_type, question_text, marks, options, correct_answer, hint
            FROM questions
            WHERE question_set_id = %s AND is_active = TRUE
            ORDER BY question_number
        """, (set_id,))
        questions = cursor.fetchall()

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['#', 'Type', 'Question', 'Marks', 'Options', 'Answer', 'Hint'])

        for q in questions:
            options = ''
            if q['options']:
                try:
                    opts = json.loads(q['options']) if isinstance(q['options'], str) else q['options']
                    options = ' | '.join(opts) if isinstance(opts, list) else str(opts)
                except:
                    pass

            writer.writerow([
                q['question_number'],
                q['question_type'],
                q['question_text'],
                q['marks'],
                options,
                q['correct_answer'],
                q['hint'] or ''
            ])

        response = make_response(output.getvalue())
        response.headers['Content-Type'] = 'text/csv'
        response.headers['Content-Disposition'] = f'attachment; filename="{question_set["title"].replace(" ", "_")}.csv"'

        return response

    finally:
        cursor.close()
        conn.close()


@questions_bp.route('/export/pdf/<int:set_id>')
@role_required('Admin')
def export_pdf(set_id):
    """Export question set as PDF"""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT qs.*, s.name as subject_name
            FROM question_sets qs
            JOIN subjects s ON qs.subject_id = s.id
            WHERE qs.id = %s
        """, (set_id,))
        question_set = cursor.fetchone()

        if not question_set:
            return jsonify({'error': 'Not found'}), 404

        cursor.execute("""
            SELECT * FROM questions
            WHERE question_set_id = %s AND is_active = TRUE
            ORDER BY question_number
        """, (set_id,))
        questions = cursor.fetchall()

        # Generate PDF using reportlab
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch, cm
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_CENTER, TA_LEFT

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=2*cm, leftMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm)

        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(name='Title2', fontSize=18, spaceAfter=12, alignment=TA_CENTER, fontName='Helvetica-Bold'))
        styles.add(ParagraphStyle(name='Subtitle', fontSize=12, spaceAfter=20, alignment=TA_CENTER, textColor=colors.grey))
        styles.add(ParagraphStyle(name='QuestionNum', fontSize=11, fontName='Helvetica-Bold', textColor=colors.HexColor('#0078D4')))
        styles.add(ParagraphStyle(name='QuestionText', fontSize=11, spaceAfter=6, leading=14))
        styles.add(ParagraphStyle(name='Option', fontSize=10, leftIndent=20, spaceAfter=3))

        elements = []

        # Header
        elements.append(Paragraph("Y6 Practice Exam", styles['Title2']))
        elements.append(Paragraph(f"{question_set['title']}", styles['Title']))
        elements.append(Paragraph(f"{question_set['subject_name']} | {question_set['total_marks']} marks | {question_set['duration_minutes']} minutes", styles['Subtitle']))
        elements.append(Spacer(1, 0.5*inch))

        # Questions
        for q in questions:
            # Question number and type
            q_type = q['question_type'].upper().replace('_', ' ')
            elements.append(Paragraph(f"Question {q['question_number']} ({q_type}) - {q['marks']} mark(s)", styles['QuestionNum']))

            # Question text
            elements.append(Paragraph(q['question_text'], styles['QuestionText']))

            # Options for MCQ
            if q['question_type'] == 'mcq' and q['options']:
                try:
                    options = json.loads(q['options']) if isinstance(q['options'], str) else q['options']
                    if isinstance(options, list):
                        for i, opt in enumerate(options):
                            letter = chr(65 + i)  # A, B, C, D
                            elements.append(Paragraph(f"({letter}) {opt}", styles['Option']))
                except:
                    pass

            # Space between questions
            elements.append(Spacer(1, 0.3*inch))

        # Build PDF
        doc.build(elements)
        buffer.seek(0)

        response = make_response(buffer.getvalue())
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename="{question_set["title"].replace(" ", "_")}.pdf"'

        AuditLogger.log_action(request.current_user['id'], 'export_questions_pdf',
                              resource_type='question_set', resource_id=str(set_id),
                              ip_address=request.remote_addr)

        return response

    finally:
        cursor.close()
        conn.close()


@questions_bp.route('/export/pdf/<int:set_id>/answers')
@role_required('Admin')
def export_pdf_with_answers(set_id):
    """Export question set as PDF with answers (answer key)"""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT qs.*, s.name as subject_name
            FROM question_sets qs
            JOIN subjects s ON qs.subject_id = s.id
            WHERE qs.id = %s
        """, (set_id,))
        question_set = cursor.fetchone()

        if not question_set:
            return jsonify({'error': 'Not found'}), 404

        cursor.execute("""
            SELECT * FROM questions
            WHERE question_set_id = %s AND is_active = TRUE
            ORDER BY question_number
        """, (set_id,))
        questions = cursor.fetchall()

        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch, cm
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_CENTER

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=2*cm, leftMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm)

        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(name='Title2', fontSize=18, spaceAfter=12, alignment=TA_CENTER, fontName='Helvetica-Bold'))
        styles.add(ParagraphStyle(name='Subtitle', fontSize=12, spaceAfter=20, alignment=TA_CENTER, textColor=colors.grey))
        styles.add(ParagraphStyle(name='QuestionNum', fontSize=11, fontName='Helvetica-Bold', textColor=colors.HexColor('#0078D4')))
        styles.add(ParagraphStyle(name='QuestionText', fontSize=11, spaceAfter=6, leading=14))
        styles.add(ParagraphStyle(name='Option', fontSize=10, leftIndent=20, spaceAfter=3))
        styles.add(ParagraphStyle(name='Answer', fontSize=10, leftIndent=20, spaceAfter=3, textColor=colors.HexColor('#107C10'), fontName='Helvetica-Bold'))

        elements = []

        # Header
        elements.append(Paragraph("Y6 Practice Exam - ANSWER KEY", styles['Title2']))
        elements.append(Paragraph(f"{question_set['title']}", styles['Title']))
        elements.append(Paragraph(f"{question_set['subject_name']} | {question_set['total_marks']} marks", styles['Subtitle']))
        elements.append(Spacer(1, 0.5*inch))

        # Questions with answers
        for q in questions:
            q_type = q['question_type'].upper().replace('_', ' ')
            elements.append(Paragraph(f"Question {q['question_number']} ({q_type}) - {q['marks']} mark(s)", styles['QuestionNum']))
            elements.append(Paragraph(q['question_text'], styles['QuestionText']))

            if q['question_type'] == 'mcq' and q['options']:
                try:
                    options = json.loads(q['options']) if isinstance(q['options'], str) else q['options']
                    if isinstance(options, list):
                        for i, opt in enumerate(options):
                            letter = chr(65 + i)
                            style = styles['Answer'] if opt.lower() == q['correct_answer'].lower() else styles['Option']
                            prefix = "* " if opt.lower() == q['correct_answer'].lower() else ""
                            elements.append(Paragraph(f"{prefix}({letter}) {opt}", style))
                except:
                    pass
            else:
                elements.append(Paragraph(f"Answer: {q['correct_answer']}", styles['Answer']))

            elements.append(Spacer(1, 0.3*inch))

        doc.build(elements)
        buffer.seek(0)

        response = make_response(buffer.getvalue())
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename="{question_set["title"].replace(" ", "_")}_ANSWERS.pdf"'

        return response

    finally:
        cursor.close()
        conn.close()


@questions_bp.route('/preview/<int:set_id>')
@role_required('Admin')
def preview_set(set_id):
    """Preview question set in browser"""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT qs.*, s.name as subject_name, s.code as subject_code
            FROM question_sets qs
            JOIN subjects s ON qs.subject_id = s.id
            WHERE qs.id = %s
        """, (set_id,))
        question_set = cursor.fetchone()

        if not question_set:
            return "Question set not found", 404

        cursor.execute("""
            SELECT * FROM questions
            WHERE question_set_id = %s AND is_active = TRUE
            ORDER BY question_number
        """, (set_id,))
        questions = cursor.fetchall()

        for q in questions:
            if q['options']:
                try:
                    q['options'] = json.loads(q['options']) if isinstance(q['options'], str) else q['options']
                except:
                    q['options'] = []

        return render_template('admin/question_preview.html',
                             question_set=question_set,
                             questions=questions,
                             user=request.current_user)

    finally:
        cursor.close()
        conn.close()


@questions_bp.route('/print/<int:set_id>')
@role_required('Admin')
def print_exam_paper(set_id):
    """Render a printable exam paper template with optional answers"""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # Check if answers should be shown (query param: ?answers=true)
    show_answers = request.args.get('answers', 'false').lower() in ('true', '1', 'yes')

    try:
        # Get question set info
        cursor.execute("""
            SELECT qs.*, s.name as subject_name, s.code as subject_code
            FROM question_sets qs
            JOIN subjects s ON qs.subject_id = s.id
            WHERE qs.id = %s
        """, (set_id,))
        question_set = cursor.fetchone()

        if not question_set:
            return "Question set not found", 404

        # Get questions
        cursor.execute("""
            SELECT * FROM questions
            WHERE question_set_id = %s AND is_active = TRUE
            ORDER BY question_number
        """, (set_id,))
        questions = cursor.fetchall()

        # Parse JSON options
        for q in questions:
            if q['options']:
                try:
                    q['options'] = json.loads(q['options']) if isinstance(q['options'], str) else q['options']
                except:
                    q['options'] = []

        return render_template('admin/question_print.html',
                             question_set=question_set,
                             questions=questions,
                             show_answers=show_answers,
                             user=request.current_user)

    finally:
        cursor.close()
        conn.close()
