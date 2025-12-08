#!/usr/bin/env python3
"""
Y6 Practice Exam - Export Questions
Export all questions from database to JSON files (subject-wise)
These files contain Y6 Cambridge curriculum questions and should be versioned.
"""

import sys
import os
import json
from pathlib import Path
from datetime import datetime

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dbs.connection import get_connection

# Output directory
EXPORT_DIR = PROJECT_ROOT / "data" / "questions"


def export_questions():
    """Export all questions to JSON files organized by subject"""

    print("=" * 60)
    print("  Y6 Practice Exam - Question Export")
    print("  Cambridge Curriculum Data")
    print("=" * 60)
    print()

    # Create export directory
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # Get all subjects
        cursor.execute("SELECT * FROM subjects ORDER BY id")
        subjects = cursor.fetchall()

        export_summary = {
            "exported_at": datetime.now().isoformat(),
            "version": "1.0.0",
            "curriculum": "Cambridge Primary Year 6",
            "subjects": []
        }

        for subject in subjects:
            print(f"\nExporting {subject['name']}...")

            # Get question sets for this subject
            cursor.execute("""
                SELECT qs.*,
                       (SELECT COUNT(*) FROM questions q WHERE q.question_set_id = qs.id) as question_count
                FROM question_sets qs
                WHERE qs.subject_id = %s AND qs.is_active = TRUE
                ORDER BY qs.id
            """, (subject['id'],))
            question_sets = cursor.fetchall()

            subject_data = {
                "subject": {
                    "id": subject['id'],
                    "code": subject['code'],
                    "name": subject['name'],
                    "color": subject.get('color', '#0078D4')
                },
                "question_sets": []
            }

            total_questions = 0

            for qs in question_sets:
                # Get questions for this set
                cursor.execute("""
                    SELECT q.question_number, q.question_type, q.question_text,
                           q.question_html, q.image_url, q.options, q.correct_answer,
                           q.matching_pairs, q.labels, q.explanation, q.hint, q.marks,
                           q.drawing_template
                    FROM questions q
                    WHERE q.question_set_id = %s AND q.is_active = TRUE
                    ORDER BY q.question_number
                """, (qs['id'],))
                questions = cursor.fetchall()

                # Parse JSON fields
                for q in questions:
                    if q['options'] and isinstance(q['options'], str):
                        try:
                            q['options'] = json.loads(q['options'])
                        except:
                            pass
                    if q['matching_pairs'] and isinstance(q['matching_pairs'], str):
                        try:
                            q['matching_pairs'] = json.loads(q['matching_pairs'])
                        except:
                            pass
                    if q['labels'] and isinstance(q['labels'], str):
                        try:
                            q['labels'] = json.loads(q['labels'])
                        except:
                            pass
                    if q['drawing_template'] and isinstance(q['drawing_template'], str):
                        try:
                            q['drawing_template'] = json.loads(q['drawing_template'])
                        except:
                            pass

                set_data = {
                    "title": qs['title'],
                    "description": qs.get('description', ''),
                    "duration_minutes": qs.get('duration_minutes', 60),
                    "difficulty": qs.get('difficulty', 'medium'),
                    "questions": questions
                }

                subject_data["question_sets"].append(set_data)
                total_questions += len(questions)
                print(f"  - {qs['title']}: {len(questions)} questions")

            # Save subject file
            filename = f"{subject['code'].lower()}_questions.json"
            filepath = EXPORT_DIR / filename

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(subject_data, f, indent=2, ensure_ascii=False, default=str)

            print(f"  Saved to: {filepath}")
            print(f"  Total: {total_questions} questions in {len(question_sets)} sets")

            export_summary["subjects"].append({
                "code": subject['code'],
                "name": subject['name'],
                "file": filename,
                "question_sets": len(question_sets),
                "total_questions": total_questions
            })

        # Save summary
        summary_path = EXPORT_DIR / "manifest.json"
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump(export_summary, f, indent=2)

        print(f"\n{'=' * 60}")
        print("Export Complete!")
        print(f"{'=' * 60}")
        print(f"\nFiles saved to: {EXPORT_DIR}")
        print("\nSummary:")
        for s in export_summary["subjects"]:
            print(f"  - {s['name']}: {s['total_questions']} questions")
        print(f"\nManifest: {summary_path}")

    finally:
        cursor.close()
        conn.close()


def export_to_csv():
    """Export questions to CSV format for spreadsheet editing"""
    import csv

    print("\nExporting to CSV format...")

    CSV_DIR = EXPORT_DIR / "csv"
    CSV_DIR.mkdir(parents=True, exist_ok=True)

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("SELECT * FROM subjects ORDER BY id")
        subjects = cursor.fetchall()

        for subject in subjects:
            cursor.execute("""
                SELECT q.*, qs.title as question_set_title
                FROM questions q
                JOIN question_sets qs ON q.question_set_id = qs.id
                WHERE qs.subject_id = %s AND q.is_active = TRUE
                ORDER BY qs.id, q.question_number
            """, (subject['id'],))
            questions = cursor.fetchall()

            if not questions:
                continue

            filename = f"{subject['code'].lower()}_questions.csv"
            filepath = CSV_DIR / filename

            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=[
                    'question_set_title', 'question_number', 'question_type',
                    'question_text', 'options', 'correct_answer', 'matching_pairs',
                    'labels', 'explanation', 'hint', 'marks', 'drawing_template'
                ])
                writer.writeheader()

                for q in questions:
                    writer.writerow({
                        'question_set_title': q['question_set_title'],
                        'question_number': q['question_number'],
                        'question_type': q['question_type'],
                        'question_text': q['question_text'],
                        'options': q['options'],
                        'correct_answer': q['correct_answer'],
                        'matching_pairs': q['matching_pairs'],
                        'labels': q.get('labels', ''),
                        'explanation': q.get('explanation', ''),
                        'hint': q.get('hint', ''),
                        'marks': q['marks'],
                        'drawing_template': q.get('drawing_template', '')
                    })

            print(f"  {subject['name']}: {filepath}")

    finally:
        cursor.close()
        conn.close()


if __name__ == '__main__':
    export_questions()

    if '--csv' in sys.argv:
        export_to_csv()

    print("\nDone!")
