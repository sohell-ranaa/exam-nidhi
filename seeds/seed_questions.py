"""
Y6 Practice Exam - Question Seeder
Seeds 500 question sets (125 per subject) with Cambridge Y6 level questions
"""

import sys
import json
import random
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "dbs"))

from dbs.connection import get_connection
from src.core.auth import PasswordManager

# ============================================================================
# QUESTION BANKS BY SUBJECT
# ============================================================================

ENGLISH_QUESTIONS = {
    'grammar': [
        {'text': 'Choose the correct word to complete the sentence: She ____ to the store yesterday.', 'type': 'mcq', 'options': ['go', 'goes', 'went', 'going'], 'answer': 'went'},
        {'text': 'Which word is a noun? The quick brown fox jumps over the lazy dog.', 'type': 'mcq', 'options': ['quick', 'jumps', 'over', 'fox'], 'answer': 'fox'},
        {'text': 'Select the correct form: If I ____ rich, I would travel the world.', 'type': 'mcq', 'options': ['am', 'was', 'were', 'be'], 'answer': 'were'},
        {'text': 'Which sentence uses the correct punctuation?', 'type': 'mcq', 'options': ["Its a lovely day.", "It's a lovely day.", "Its' a lovely day.", "Its a lovely day!"], 'answer': "It's a lovely day."},
        {'text': 'Identify the adverb: The cat moved silently through the garden.', 'type': 'mcq', 'options': ['cat', 'moved', 'silently', 'garden'], 'answer': 'silently'},
        {'text': 'Choose the correct conjunction: I wanted to go outside, ____ it was raining.', 'type': 'mcq', 'options': ['and', 'but', 'or', 'so'], 'answer': 'but'},
        {'text': 'Which word is spelled correctly?', 'type': 'mcq', 'options': ['recieve', 'receive', 'receve', 'receeve'], 'answer': 'receive'},
        {'text': 'Select the correct plural: The ____ were playing in the garden.', 'type': 'mcq', 'options': ['childs', 'childes', 'children', 'childern'], 'answer': 'children'},
    ],
    'vocabulary': [
        {'text': 'What does "enormous" mean?', 'type': 'mcq', 'options': ['tiny', 'very large', 'colorful', 'fast'], 'answer': 'very large'},
        {'text': 'Choose the synonym for "happy":', 'type': 'mcq', 'options': ['sad', 'joyful', 'angry', 'tired'], 'answer': 'joyful'},
        {'text': 'What is the antonym of "ancient"?', 'type': 'mcq', 'options': ['old', 'historic', 'modern', 'dusty'], 'answer': 'modern'},
        {'text': 'Which word means "to move quickly"?', 'type': 'mcq', 'options': ['crawl', 'stroll', 'dash', 'amble'], 'answer': 'dash'},
        {'text': 'What does "courageous" mean?', 'type': 'mcq', 'options': ['scared', 'brave', 'weak', 'quiet'], 'answer': 'brave'},
    ],
    'comprehension': [
        {'text': 'The sun was setting behind the mountains, painting the sky in shades of orange and pink. Why is the sky described as orange and pink?', 'type': 'written', 'answer': 'Because the sun is setting and its light creates these colors in the sky'},
        {'text': 'Maya felt nervous before her first piano recital, but once she started playing, the music flowed naturally. How did Maya feel before the recital?', 'type': 'mcq', 'options': ['Confident', 'Nervous', 'Excited', 'Bored'], 'answer': 'Nervous'},
        {'text': 'Explain why characters in stories often face challenges.', 'type': 'written', 'answer': 'Characters face challenges to create conflict, show growth, and make the story interesting for readers'},
    ]
}

MATH_QUESTIONS = {
    'arithmetic': [
        {'text': 'What is 456 + 789?', 'type': 'fill_blank', 'answer': '1245'},
        {'text': 'Calculate: 1000 - 347', 'type': 'fill_blank', 'answer': '653'},
        {'text': 'What is 25 x 12?', 'type': 'fill_blank', 'answer': '300'},
        {'text': 'Divide: 144 ÷ 12', 'type': 'fill_blank', 'answer': '12'},
        {'text': 'What is 5 + 9 × 3?', 'type': 'mcq', 'options': ['42', '32', '27', '17'], 'answer': '32'},
        {'text': 'Calculate: 6 × (4 + 5)', 'type': 'mcq', 'options': ['29', '54', '45', '33'], 'answer': '54'},
        {'text': 'What is 3.5 + 2.7?', 'type': 'fill_blank', 'answer': '6.2'},
        {'text': 'What is 15% of 200?', 'type': 'fill_blank', 'answer': '30'},
    ],
    'fractions': [
        {'text': 'What is 1/2 + 1/4?', 'type': 'mcq', 'options': ['2/6', '3/4', '1/6', '2/4'], 'answer': '3/4'},
        {'text': 'Simplify: 8/12', 'type': 'mcq', 'options': ['4/6', '2/3', '2/4', '1/2'], 'answer': '2/3'},
        {'text': 'Convert 0.75 to a fraction:', 'type': 'mcq', 'options': ['3/4', '1/2', '7/5', '5/7'], 'answer': '3/4'},
        {'text': 'What is 2/5 of 50?', 'type': 'fill_blank', 'answer': '20'},
    ],
    'geometry': [
        {'text': 'What is the area of a rectangle with length 8cm and width 5cm?', 'type': 'mcq', 'options': ['13cm²', '40cm²', '26cm²', '80cm²'], 'answer': '40cm²'},
        {'text': 'How many degrees are in a right angle?', 'type': 'fill_blank', 'answer': '90'},
        {'text': 'What is the perimeter of a square with side 7cm?', 'type': 'fill_blank', 'answer': '28'},
        {'text': 'A triangle has angles of 60° and 80°. What is the third angle?', 'type': 'fill_blank', 'answer': '40'},
    ],
    'word_problems': [
        {'text': 'Sarah has 48 stickers. She gives 1/4 to her friend. How many stickers does she give away?', 'type': 'fill_blank', 'answer': '12'},
        {'text': 'A shop sells apples for RM2.50 each. How much do 6 apples cost?', 'type': 'fill_blank', 'answer': '15'},
        {'text': 'If a train travels at 80km/h, how far does it travel in 3 hours?', 'type': 'fill_blank', 'answer': '240'},
    ]
}

ICT_QUESTIONS = {
    'programming': [
        {'text': 'What is a variable in programming?', 'type': 'mcq', 'options': ['A fixed number', 'A value that can change', 'A type of loop', 'A hardware part'], 'answer': 'A value that can change'},
        {'text': 'Which structure repeats a block of code multiple times?', 'type': 'mcq', 'options': ['Selection', 'Loop', 'Sequence', 'Variable'], 'answer': 'Loop'},
        {'text': 'What does the "IF" statement check?', 'type': 'mcq', 'options': ['A condition', 'A variable name', 'A file', 'A website'], 'answer': 'A condition'},
        {'text': 'In Scratch, which block makes a sprite move forward?', 'type': 'mcq', 'options': ['Say', 'Move', 'Wait', 'Repeat'], 'answer': 'Move'},
        {'text': 'Explain why planning with a flowchart is important before programming.', 'type': 'written', 'answer': 'Planning helps organize steps, find errors early, and makes the code easier to write and understand'},
    ],
    'hardware': [
        {'text': 'Which device is used to display information on a screen?', 'type': 'mcq', 'options': ['Keyboard', 'Mouse', 'Monitor', 'Speaker'], 'answer': 'Monitor'},
        {'text': 'What is the main function of RAM?', 'type': 'mcq', 'options': ['Store files permanently', 'Temporary memory for running programs', 'Connect to the internet', 'Display graphics'], 'answer': 'Temporary memory for running programs'},
        {'text': 'Which device is an input device?', 'type': 'mcq', 'options': ['Printer', 'Speaker', 'Keyboard', 'Monitor'], 'answer': 'Keyboard'},
        {'text': 'What does CPU stand for?', 'type': 'fill_blank', 'answer': 'Central Processing Unit'},
    ],
    'software': [
        {'text': 'What type of software is Microsoft Word?', 'type': 'mcq', 'options': ['Operating system', 'Word processor', 'Web browser', 'Game'], 'answer': 'Word processor'},
        {'text': 'Which is an example of an operating system?', 'type': 'mcq', 'options': ['Google Chrome', 'Microsoft Word', 'Windows', 'Photoshop'], 'answer': 'Windows'},
        {'text': 'What is the purpose of antivirus software?', 'type': 'written', 'answer': 'To protect the computer from viruses and malware, keeping files and data safe'},
    ],
    'internet': [
        {'text': 'What does WWW stand for?', 'type': 'fill_blank', 'answer': 'World Wide Web'},
        {'text': 'Which is a safe practice when using the internet?', 'type': 'mcq', 'options': ['Share your password', 'Use strong passwords', 'Click all links', 'Share personal info'], 'answer': 'Use strong passwords'},
        {'text': 'What is the purpose of a search engine?', 'type': 'mcq', 'options': ['Create websites', 'Find information online', 'Send emails', 'Play games'], 'answer': 'Find information online'},
    ]
}

SCIENCE_QUESTIONS = {
    'biology': [
        {'text': 'What is the largest organ in the human body?', 'type': 'mcq', 'options': ['Heart', 'Brain', 'Skin', 'Liver'], 'answer': 'Skin'},
        {'text': 'What do plants need to make their own food?', 'type': 'mcq', 'options': ['Only water', 'Sunlight, water, and carbon dioxide', 'Only sunlight', 'Soil only'], 'answer': 'Sunlight, water, and carbon dioxide'},
        {'text': 'What is the process called when plants make food using sunlight?', 'type': 'fill_blank', 'answer': 'Photosynthesis'},
        {'text': 'Which part of the plant absorbs water from the soil?', 'type': 'mcq', 'options': ['Leaves', 'Stem', 'Roots', 'Flowers'], 'answer': 'Roots'},
        {'text': 'Name the organ that pumps blood around the body.', 'type': 'fill_blank', 'answer': 'Heart'},
        {'text': 'What is the function of the lungs?', 'type': 'written', 'answer': 'To take in oxygen from the air and release carbon dioxide from the body'},
    ],
    'physics': [
        {'text': 'What force pulls objects towards the Earth?', 'type': 'mcq', 'options': ['Friction', 'Gravity', 'Magnetism', 'Air resistance'], 'answer': 'Gravity'},
        {'text': 'What is the unit of force?', 'type': 'mcq', 'options': ['Meter', 'Newton', 'Kilogram', 'Second'], 'answer': 'Newton'},
        {'text': 'Which type of energy does a moving car have?', 'type': 'mcq', 'options': ['Potential energy', 'Kinetic energy', 'Sound energy', 'Light energy'], 'answer': 'Kinetic energy'},
        {'text': 'What travels faster: sound or light?', 'type': 'mcq', 'options': ['Sound', 'Light', 'They travel at the same speed', 'It depends'], 'answer': 'Light'},
    ],
    'chemistry': [
        {'text': 'What are the three states of matter?', 'type': 'written', 'answer': 'Solid, liquid, and gas'},
        {'text': 'What happens to water when it is heated to 100°C?', 'type': 'mcq', 'options': ['It freezes', 'It boils', 'Nothing', 'It becomes solid'], 'answer': 'It boils'},
        {'text': 'Which gas do we breathe in?', 'type': 'mcq', 'options': ['Carbon dioxide', 'Nitrogen', 'Oxygen', 'Hydrogen'], 'answer': 'Oxygen'},
        {'text': 'What is the chemical symbol for water?', 'type': 'fill_blank', 'answer': 'H2O'},
    ],
    'earth_science': [
        {'text': 'What causes day and night?', 'type': 'mcq', 'options': ['The Moon orbiting Earth', 'Earth rotating on its axis', 'Earth orbiting the Sun', 'The Sun moving'], 'answer': 'Earth rotating on its axis'},
        {'text': 'Which layer of the Earth is the hottest?', 'type': 'mcq', 'options': ['Crust', 'Mantle', 'Outer core', 'Inner core'], 'answer': 'Inner core'},
        {'text': 'What causes earthquakes?', 'type': 'written', 'answer': 'Movement of tectonic plates beneath the Earth\'s surface'},
    ]
}


def generate_question_set_title(subject_id, topic, set_number):
    """Generate a realistic question set title"""
    titles = {
        1: [f"English Grammar Practice {set_number}", f"Reading Comprehension {set_number}",
            f"Vocabulary Builder {set_number}", f"English Skills Test {set_number}"],
        2: [f"Mathematics Practice {set_number}", f"Problem Solving {set_number}",
            f"Arithmetic Challenge {set_number}", f"Math Skills Test {set_number}"],
        3: [f"ICT Knowledge Test {set_number}", f"Programming Basics {set_number}",
            f"Computer Skills {set_number}", f"Digital Literacy {set_number}"],
        4: [f"Science Discovery {set_number}", f"Nature & Science {set_number}",
            f"Science Explorer {set_number}", f"Scientific Thinking {set_number}"]
    }
    return random.choice(titles.get(subject_id, [f"Practice Test {set_number}"]))


def get_questions_for_subject(subject_id, num_questions=10):
    """Get random questions for a subject"""
    question_banks = {
        1: ENGLISH_QUESTIONS,
        2: MATH_QUESTIONS,
        3: ICT_QUESTIONS,
        4: SCIENCE_QUESTIONS
    }

    bank = question_banks.get(subject_id, {})
    all_questions = []

    for topic, questions in bank.items():
        for q in questions:
            q['topic'] = topic
            all_questions.append(q)

    # Randomly select questions
    selected = random.sample(all_questions, min(num_questions, len(all_questions)))
    return selected


def seed_admin_user():
    """Create admin user"""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # Check if admin exists
        cursor.execute("SELECT id FROM users WHERE email = 'admin@springgate.edu.my'")
        if cursor.fetchone():
            print("Admin user already exists")
            return

        password_hash = PasswordManager.hash_password('admin123')

        cursor.execute("""
            INSERT INTO users (email, password_hash, full_name, role_id, is_active, is_email_verified)
            VALUES ('admin@springgate.edu.my', %s, 'Admin', 1, TRUE, TRUE)
        """, (password_hash,))

        conn.commit()
        print("Admin user created: admin@springgate.edu.my / admin123")

    finally:
        cursor.close()
        conn.close()


def seed_student_user():
    """Create student user (Rifah)"""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("SELECT id FROM users WHERE email = 'rifah@springgate.edu.my'")
        if cursor.fetchone():
            print("Student user already exists")
            return

        password_hash = PasswordManager.hash_password('rifah123')

        cursor.execute("""
            INSERT INTO users (email, password_hash, full_name, role_id, is_active, is_email_verified)
            VALUES ('rifah@springgate.edu.my', %s, 'Rifah', 2, TRUE, TRUE)
        """, (password_hash,))

        conn.commit()
        print("Student user created: rifah@springgate.edu.my / rifah123")

    finally:
        cursor.close()
        conn.close()


def seed_question_sets(sets_per_subject=125):
    """Seed 500 question sets (125 per subject)"""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    subjects = [
        (1, 'English'),
        (2, 'Mathematics'),
        (3, 'ICT'),
        (4, 'Science')
    ]

    total_created = 0

    try:
        for subject_id, subject_name in subjects:
            print(f"\nSeeding {subject_name} question sets...")

            for i in range(1, sets_per_subject + 1):
                # Create question set
                title = generate_question_set_title(subject_id, None, i)
                num_questions = random.randint(8, 15)
                total_marks = num_questions * random.choice([1, 2])
                difficulty = random.choice(['easy', 'medium', 'hard'])
                duration = random.choice([30, 45, 60])

                cursor.execute("""
                    INSERT INTO question_sets (subject_id, title, total_marks, duration_minutes, difficulty)
                    VALUES (%s, %s, %s, %s, %s)
                """, (subject_id, title, total_marks, duration, difficulty))

                question_set_id = cursor.lastrowid

                # Add questions
                questions = get_questions_for_subject(subject_id, num_questions)

                for q_num, q in enumerate(questions, 1):
                    marks = 1 if q['type'] == 'mcq' else random.choice([1, 2])
                    options_json = json.dumps(q.get('options')) if q.get('options') else None

                    cursor.execute("""
                        INSERT INTO questions
                        (question_set_id, question_number, question_type, question_text,
                         marks, correct_answer, options)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, (question_set_id, q_num, q['type'], q['text'],
                          marks, q['answer'], options_json))

                total_created += 1

                if i % 25 == 0:
                    print(f"  Created {i}/{sets_per_subject} sets for {subject_name}")
                    conn.commit()

            conn.commit()
            print(f"Completed {subject_name}: {sets_per_subject} question sets")

        print(f"\n{'='*50}")
        print(f"Total question sets created: {total_created}")
        print(f"{'='*50}")

    except Exception as e:
        conn.rollback()
        print(f"Error seeding questions: {e}")
        raise

    finally:
        cursor.close()
        conn.close()


def main():
    """Main seeding function"""
    print("="*60)
    print("Y6 PRACTICE EXAM - DATABASE SEEDER")
    print("="*60)

    print("\n1. Creating admin user...")
    seed_admin_user()

    print("\n2. Creating student user (Rifah)...")
    seed_student_user()

    print("\n3. Seeding 500 question sets (125 per subject)...")
    seed_question_sets(125)

    print("\n" + "="*60)
    print("SEEDING COMPLETE!")
    print("="*60)
    print("\nCredentials:")
    print("  Admin: admin@springgate.edu.my / admin123")
    print("  Student: rifah@springgate.edu.my / rifah123")
    print("\nRun the app: python app.py")
    print("Access: http://localhost:5001")


if __name__ == "__main__":
    main()
