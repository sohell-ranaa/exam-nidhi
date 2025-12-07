"""
Y6 Practice Exam - Analytics Dashboard
Charts, statistics, and performance insights
"""

from flask import Blueprint, request, jsonify, render_template
from datetime import datetime, timedelta
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src" / "core"))
sys.path.insert(0, str(PROJECT_ROOT / "dbs"))

from src.core.auth import role_required
from src.core.cache import get_cache, cache_key, CACHE_TTL
from dbs.connection import get_connection

analytics_bp = Blueprint('analytics', __name__, url_prefix='/analytics')


@analytics_bp.route('/')
@role_required('Admin')
def dashboard():
    """Analytics dashboard"""
    return render_template('admin/analytics.html', user=request.current_user)


@analytics_bp.route('/api/overview')
@role_required('Admin')
def api_overview():
    """Get overview statistics"""
    cache = get_cache()
    key = cache_key('analytics', 'overview')

    # Check cache
    cached = cache.get(key)
    if cached:
        return jsonify(cached)

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # Total stats
        cursor.execute("""
            SELECT
                (SELECT COUNT(*) FROM users WHERE role_id = 2 AND is_active = TRUE) as total_students,
                (SELECT COUNT(*) FROM question_sets WHERE is_active = TRUE) as total_question_sets,
                (SELECT COUNT(*) FROM questions WHERE is_active = TRUE) as total_questions,
                (SELECT COUNT(*) FROM practice_exams) as total_exams,
                (SELECT COUNT(*) FROM practice_exams WHERE status = 'released') as completed_exams,
                (SELECT COUNT(*) FROM practice_exams WHERE status = 'submitted') as pending_grading,
                (SELECT AVG(percentage) FROM practice_exams WHERE status = 'released') as avg_score
        """)
        stats = cursor.fetchone()

        # This week's activity
        cursor.execute("""
            SELECT COUNT(*) as count FROM practice_exams
            WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
        """)
        week_exams = cursor.fetchone()['count']

        # Last week comparison
        cursor.execute("""
            SELECT COUNT(*) as count FROM practice_exams
            WHERE created_at >= DATE_SUB(NOW(), INTERVAL 14 DAY)
            AND created_at < DATE_SUB(NOW(), INTERVAL 7 DAY)
        """)
        last_week = cursor.fetchone()['count']

        result = {
            'total_students': stats['total_students'] or 0,
            'total_question_sets': stats['total_question_sets'] or 0,
            'total_questions': stats['total_questions'] or 0,
            'total_exams': stats['total_exams'] or 0,
            'completed_exams': stats['completed_exams'] or 0,
            'pending_grading': stats['pending_grading'] or 0,
            'avg_score': round(stats['avg_score'] or 0, 1),
            'week_exams': week_exams,
            'week_change': week_exams - last_week
        }

        # Cache for 5 minutes
        cache.set(key, result, 300)

        return jsonify(result)

    finally:
        cursor.close()
        conn.close()


@analytics_bp.route('/api/performance-trend')
@role_required('Admin')
def api_performance_trend():
    """Get performance trend over time"""
    days = int(request.args.get('days', 30))

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT
                DATE(released_at) as date,
                COUNT(*) as exams,
                AVG(percentage) as avg_score
            FROM practice_exams
            WHERE status = 'released'
            AND released_at >= DATE_SUB(NOW(), INTERVAL %s DAY)
            GROUP BY DATE(released_at)
            ORDER BY date
        """, (days,))
        data = cursor.fetchall()

        result = {
            'labels': [d['date'].strftime('%d %b') for d in data],
            'exams': [d['exams'] for d in data],
            'scores': [round(d['avg_score'] or 0, 1) for d in data]
        }

        return jsonify(result)

    finally:
        cursor.close()
        conn.close()


@analytics_bp.route('/api/subject-performance')
@role_required('Admin')
def api_subject_performance():
    """Get performance breakdown by subject"""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT
                s.name as subject,
                s.code,
                COUNT(pe.id) as total_exams,
                AVG(pe.percentage) as avg_score,
                MAX(pe.percentage) as best_score,
                MIN(pe.percentage) as lowest_score
            FROM subjects s
            LEFT JOIN question_sets qs ON qs.subject_id = s.id
            LEFT JOIN practice_exams pe ON pe.question_set_id = qs.id AND pe.status = 'released'
            WHERE s.is_active = TRUE
            GROUP BY s.id, s.name, s.code
            ORDER BY s.name
        """)
        data = cursor.fetchall()

        result = {
            'subjects': [d['subject'] for d in data],
            'codes': [d['code'] for d in data],
            'total_exams': [d['total_exams'] or 0 for d in data],
            'avg_scores': [round(d['avg_score'] or 0, 1) for d in data],
            'best_scores': [round(d['best_score'] or 0, 1) for d in data],
            'lowest_scores': [round(d['lowest_score'] or 0, 1) for d in data]
        }

        return jsonify(result)

    finally:
        cursor.close()
        conn.close()


@analytics_bp.route('/api/question-type-stats')
@role_required('Admin')
def api_question_type_stats():
    """Get statistics by question type"""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT
                q.question_type,
                COUNT(DISTINCT q.id) as question_count,
                COUNT(sa.id) as answer_count,
                SUM(CASE WHEN sa.is_correct = TRUE THEN 1 ELSE 0 END) as correct_count,
                AVG(CASE WHEN sa.marks_awarded IS NOT NULL THEN sa.marks_awarded / q.marks * 100 END) as avg_score
            FROM questions q
            LEFT JOIN student_answers sa ON sa.question_id = q.id
            WHERE q.is_active = TRUE
            GROUP BY q.question_type
        """)
        data = cursor.fetchall()

        result = {
            'types': [d['question_type'] for d in data],
            'counts': [d['question_count'] for d in data],
            'answers': [d['answer_count'] or 0 for d in data],
            'correct': [d['correct_count'] or 0 for d in data],
            'accuracy': [round(d['avg_score'] or 0, 1) for d in data]
        }

        return jsonify(result)

    finally:
        cursor.close()
        conn.close()


@analytics_bp.route('/api/student-leaderboard')
@role_required('Admin')
def api_student_leaderboard():
    """Get student leaderboard"""
    limit = int(request.args.get('limit', 10))

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT
                u.id,
                u.full_name,
                COUNT(pe.id) as total_exams,
                AVG(pe.percentage) as avg_score,
                MAX(pe.percentage) as best_score,
                SUM(pe.total_score) as total_points
            FROM users u
            LEFT JOIN practice_exams pe ON pe.student_id = u.id AND pe.status = 'released'
            WHERE u.role_id = 2 AND u.is_active = TRUE
            GROUP BY u.id, u.full_name
            HAVING total_exams > 0
            ORDER BY avg_score DESC
            LIMIT %s
        """, (limit,))
        data = cursor.fetchall()

        result = [{
            'rank': i + 1,
            'id': d['id'],
            'name': d['full_name'],
            'exams': d['total_exams'],
            'avg_score': round(d['avg_score'] or 0, 1),
            'best_score': round(d['best_score'] or 0, 1),
            'total_points': d['total_points'] or 0
        } for i, d in enumerate(data)]

        return jsonify(result)

    finally:
        cursor.close()
        conn.close()


@analytics_bp.route('/api/recent-activity')
@role_required('Admin')
def api_recent_activity():
    """Get recent exam activity"""
    limit = int(request.args.get('limit', 20))

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT
                pe.id,
                pe.status,
                pe.percentage,
                pe.submitted_at,
                pe.released_at,
                u.full_name as student_name,
                qs.title as exam_title,
                s.name as subject_name,
                s.code as subject_code
            FROM practice_exams pe
            JOIN users u ON pe.student_id = u.id
            JOIN question_sets qs ON pe.question_set_id = qs.id
            JOIN subjects s ON qs.subject_id = s.id
            ORDER BY
                CASE
                    WHEN pe.released_at IS NOT NULL THEN pe.released_at
                    WHEN pe.submitted_at IS NOT NULL THEN pe.submitted_at
                    ELSE pe.created_at
                END DESC
            LIMIT %s
        """, (limit,))
        data = cursor.fetchall()

        for d in data:
            if d['submitted_at']:
                d['submitted_at'] = d['submitted_at'].strftime('%d %b %H:%M')
            if d['released_at']:
                d['released_at'] = d['released_at'].strftime('%d %b %H:%M')
            if d['percentage']:
                d['percentage'] = round(d['percentage'], 1)

        return jsonify(data)

    finally:
        cursor.close()
        conn.close()


@analytics_bp.route('/api/difficulty-analysis')
@role_required('Admin')
def api_difficulty_analysis():
    """Analyze question difficulty based on success rate"""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT
                q.id,
                q.question_number,
                q.question_type,
                q.question_text,
                qs.title as question_set,
                s.name as subject,
                COUNT(sa.id) as attempts,
                SUM(CASE WHEN sa.is_correct = TRUE THEN 1 ELSE 0 END) as correct,
                AVG(CASE WHEN sa.is_correct IS NOT NULL THEN sa.is_correct * 100 END) as success_rate
            FROM questions q
            JOIN question_sets qs ON q.question_set_id = qs.id
            JOIN subjects s ON qs.subject_id = s.id
            LEFT JOIN student_answers sa ON sa.question_id = q.id
            WHERE q.is_active = TRUE
            GROUP BY q.id, q.question_number, q.question_type, q.question_text, qs.title, s.name
            HAVING attempts > 0
            ORDER BY success_rate ASC
            LIMIT 20
        """)
        hardest = cursor.fetchall()

        cursor.execute("""
            SELECT
                q.id,
                q.question_number,
                q.question_type,
                SUBSTRING(q.question_text, 1, 100) as question_text,
                qs.title as question_set,
                s.name as subject,
                COUNT(sa.id) as attempts,
                SUM(CASE WHEN sa.is_correct = TRUE THEN 1 ELSE 0 END) as correct,
                AVG(CASE WHEN sa.is_correct IS NOT NULL THEN sa.is_correct * 100 END) as success_rate
            FROM questions q
            JOIN question_sets qs ON q.question_set_id = qs.id
            JOIN subjects s ON qs.subject_id = s.id
            LEFT JOIN student_answers sa ON sa.question_id = q.id
            WHERE q.is_active = TRUE
            GROUP BY q.id
            HAVING attempts > 0
            ORDER BY success_rate DESC
            LIMIT 20
        """)
        easiest = cursor.fetchall()

        for q in hardest + easiest:
            if q['success_rate']:
                q['success_rate'] = round(q['success_rate'], 1)

        return jsonify({
            'hardest': hardest,
            'easiest': easiest
        })

    finally:
        cursor.close()
        conn.close()
