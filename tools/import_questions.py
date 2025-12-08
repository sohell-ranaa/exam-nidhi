#!/usr/bin/env python3
"""
Y6 Practice Exam - Import Questions
Import questions from JSON files (subject-wise)
For Y6 Cambridge curriculum data
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

# Default import directory
IMPORT_DIR = PROJECT_ROOT / "data" / "questions"


def import_questions(data_dir=None, subject_filter=None, clear_existing=False):
    """
    Import questions from JSON files

    Args:
        data_dir: Directory containing JSON files (default: data/questions)
        subject_filter: Only import specific subject code (e.g., 'ENG', 'MAT')
        clear_existing: If True, delete existing questions before import
    """

    data_dir = Path(data_dir) if data_dir else IMPORT_DIR

    print("=" * 60)
    print("  Y6 Practice Exam - Question Import")
    print("  Cambridge Curriculum Data")
    print("=" * 60)
    print(f"\nImporting from: {data_dir}")
    print()

    if not data_dir.exists():
        print(f"Error: Directory not found: {data_dir}")
        print("\nPlease ensure question files exist in the data/questions directory.")
        print("You can export from an existing database using: python tools/export_questions.py")
        return False

    # Check for manifest
    manifest_path = data_dir / "manifest.json"
    if manifest_path.exists():
        with open(manifest_path, 'r', encoding='utf-8') as f:
            manifest = json.load(f)
        print(f"Manifest found: {manifest.get('curriculum', 'Unknown')}")
        print(f"Exported: {manifest.get('exported_at', 'Unknown')}")
        print()

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # Ensure subjects exist
        ensure_subjects(cursor, conn)

        # Get subject files
        json_files = list(data_dir.glob("*_questions.json"))

        if not json_files:
            print("No question files found!")
            print("Expected files: eng_questions.json, mat_questions.json, etc.")
            return False

        total_imported = 0

        for filepath in sorted(json_files):
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            subject_info = data.get('subject', {})
            subject_code = subject_info.get('code', filepath.stem.split('_')[0].upper())

            # Apply subject filter
            if subject_filter and subject_code.upper() != subject_filter.upper():
                continue

            print(f"\nImporting {subject_info.get('name', subject_code)}...")

            # Get or create subject
            cursor.execute("SELECT id FROM subjects WHERE code = %s", (subject_code,))
            subject_row = cursor.fetchone()

            if not subject_row:
                cursor.execute("""
                    INSERT INTO subjects (code, name, color)
                    VALUES (%s, %s, %s)
                """, (subject_code, subject_info.get('name', subject_code),
                      subject_info.get('color', '#0078D4')))
                conn.commit()
                subject_id = cursor.lastrowid
            else:
                subject_id = subject_row['id']

            # Clear existing if requested
            if clear_existing:
                cursor.execute("""
                    DELETE q FROM questions q
                    JOIN question_sets qs ON q.question_set_id = qs.id
                    WHERE qs.subject_id = %s
                """, (subject_id,))
                cursor.execute("DELETE FROM question_sets WHERE subject_id = %s", (subject_id,))
                conn.commit()
                print(f"  Cleared existing questions for {subject_code}")

            # Import question sets
            for qs_data in data.get('question_sets', []):
                # Check if question set exists
                cursor.execute("""
                    SELECT id FROM question_sets
                    WHERE subject_id = %s AND title = %s
                """, (subject_id, qs_data['title']))
                existing_qs = cursor.fetchone()

                if existing_qs:
                    question_set_id = existing_qs['id']
                    print(f"  Updating: {qs_data['title']}")
                else:
                    cursor.execute("""
                        INSERT INTO question_sets (subject_id, title, description, duration_minutes, difficulty, is_active)
                        VALUES (%s, %s, %s, %s, %s, TRUE)
                    """, (
                        subject_id,
                        qs_data['title'],
                        qs_data.get('description', ''),
                        qs_data.get('duration_minutes', 60),
                        qs_data.get('difficulty', 'medium')
                    ))
                    conn.commit()
                    question_set_id = cursor.lastrowid
                    print(f"  Created: {qs_data['title']}")

                # Import questions
                questions_imported = 0
                for q in qs_data.get('questions', []):
                    # Prepare JSON fields
                    options = json.dumps(q['options']) if q.get('options') else None
                    matching_pairs = json.dumps(q['matching_pairs']) if q.get('matching_pairs') else None
                    labels = json.dumps(q['labels']) if q.get('labels') else None
                    drawing_template = json.dumps(q['drawing_template']) if q.get('drawing_template') else None

                    # Check if question exists
                    cursor.execute("""
                        SELECT id FROM questions
                        WHERE question_set_id = %s AND question_number = %s
                    """, (question_set_id, q['question_number']))
                    existing_q = cursor.fetchone()

                    if existing_q:
                        # Update existing
                        cursor.execute("""
                            UPDATE questions SET
                                question_type = %s,
                                question_text = %s,
                                question_html = %s,
                                image_url = %s,
                                options = %s,
                                correct_answer = %s,
                                matching_pairs = %s,
                                labels = %s,
                                explanation = %s,
                                hint = %s,
                                marks = %s,
                                drawing_template = %s,
                                is_active = TRUE
                            WHERE id = %s
                        """, (
                            q['question_type'],
                            q['question_text'],
                            q.get('question_html'),
                            q.get('image_url'),
                            options,
                            q.get('correct_answer'),
                            matching_pairs,
                            labels,
                            q.get('explanation'),
                            q.get('hint'),
                            q.get('marks', 1),
                            drawing_template,
                            existing_q['id']
                        ))
                    else:
                        # Insert new
                        cursor.execute("""
                            INSERT INTO questions (
                                question_set_id, question_number, question_type, question_text,
                                question_html, image_url, options, correct_answer, matching_pairs,
                                labels, explanation, hint, marks, drawing_template, is_active
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, TRUE)
                        """, (
                            question_set_id,
                            q['question_number'],
                            q['question_type'],
                            q['question_text'],
                            q.get('question_html'),
                            q.get('image_url'),
                            options,
                            q.get('correct_answer'),
                            matching_pairs,
                            labels,
                            q.get('explanation'),
                            q.get('hint'),
                            q.get('marks', 1),
                            drawing_template
                        ))

                    questions_imported += 1

                conn.commit()
                print(f"    {questions_imported} questions")
                total_imported += questions_imported

        print(f"\n{'=' * 60}")
        print(f"Import Complete!")
        print(f"{'=' * 60}")
        print(f"\nTotal questions imported: {total_imported}")
        return True

    except Exception as e:
        conn.rollback()
        print(f"\nError during import: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        cursor.close()
        conn.close()


def ensure_subjects(cursor, conn):
    """Ensure default subjects exist"""
    subjects = [
        ('ENG', 'English', '#0078D4'),
        ('MAT', 'Mathematics', '#D13438'),
        ('ICT', 'ICT', '#8764B8'),
        ('SCI', 'Science', '#107C10')
    ]

    for code, name, color in subjects:
        cursor.execute("SELECT id FROM subjects WHERE code = %s", (code,))
        if not cursor.fetchone():
            cursor.execute("""
                INSERT INTO subjects (code, name, color)
                VALUES (%s, %s, %s)
            """, (code, name, color))

    conn.commit()


def import_from_csv(csv_file, subject_code):
    """Import questions from a CSV file"""
    import csv

    print(f"Importing from CSV: {csv_file}")

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # Get subject
        cursor.execute("SELECT id FROM subjects WHERE code = %s", (subject_code,))
        subject_row = cursor.fetchone()
        if not subject_row:
            print(f"Subject not found: {subject_code}")
            return False

        subject_id = subject_row['id']

        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)

            current_set = None
            question_set_id = None
            imported = 0

            for row in reader:
                # Create/get question set
                set_title = row.get('question_set_title', 'Imported Questions')
                if set_title != current_set:
                    cursor.execute("""
                        SELECT id FROM question_sets WHERE subject_id = %s AND title = %s
                    """, (subject_id, set_title))
                    qs = cursor.fetchone()

                    if qs:
                        question_set_id = qs['id']
                    else:
                        cursor.execute("""
                            INSERT INTO question_sets (subject_id, title, is_active)
                            VALUES (%s, %s, TRUE)
                        """, (subject_id, set_title))
                        conn.commit()
                        question_set_id = cursor.lastrowid

                    current_set = set_title

                # Insert question
                cursor.execute("""
                    INSERT INTO questions (
                        question_set_id, question_number, question_type, question_text,
                        options, correct_answer, matching_pairs, labels, explanation, hint,
                        marks, drawing_template, is_active
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, TRUE)
                """, (
                    question_set_id,
                    row.get('question_number', imported + 1),
                    row.get('question_type', 'mcq'),
                    row['question_text'],
                    row.get('options'),
                    row.get('correct_answer'),
                    row.get('matching_pairs'),
                    row.get('labels'),
                    row.get('explanation'),
                    row.get('hint'),
                    row.get('marks', 1),
                    row.get('drawing_template')
                ))
                imported += 1

            conn.commit()
            print(f"Imported {imported} questions")
            return True

    except Exception as e:
        conn.rollback()
        print(f"Error: {e}")
        return False

    finally:
        cursor.close()
        conn.close()


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Import Y6 Cambridge curriculum questions')
    parser.add_argument('--dir', '-d', help='Directory containing JSON files')
    parser.add_argument('--subject', '-s', help='Import only specific subject (ENG, MAT, ICT, SCI)')
    parser.add_argument('--clear', '-c', action='store_true', help='Clear existing questions before import')
    parser.add_argument('--csv', help='Import from CSV file (requires --subject)')

    args = parser.parse_args()

    if args.csv:
        if not args.subject:
            print("Error: --subject required when importing from CSV")
            sys.exit(1)
        success = import_from_csv(args.csv, args.subject)
    else:
        success = import_questions(
            data_dir=args.dir,
            subject_filter=args.subject,
            clear_existing=args.clear
        )

    sys.exit(0 if success else 1)
