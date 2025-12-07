"""
Y6 Practice Exam - Comprehensive Question Seeder
Cambridge Year 6 Level - All Subjects with Images and Drawing Support
Spring Gate Private School, Selangor, Malaysia
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
# ENGLISH QUESTIONS - Cambridge Y6 Level
# Mix of: MCQ, Fill Blank, Written, Matching
# ============================================================================

ENGLISH_QUESTIONS = {
    'grammar': [
        # MCQ
        {'text': 'Choose the correct word: She ____ to school every day.', 'type': 'mcq', 'options': ['go', 'goes', 'going', 'gone'], 'answer': 'goes', 'marks': 1},
        {'text': 'Which sentence uses the past perfect tense correctly?', 'type': 'mcq', 'options': ['I have eaten lunch.', 'I had eaten lunch before she arrived.', 'I eat lunch daily.', 'I will have eaten.'], 'answer': 'I had eaten lunch before she arrived.', 'marks': 1},
        {'text': 'Identify the pronoun in: They visited their grandmother yesterday.', 'type': 'mcq', 'options': ['visited', 'grandmother', 'They', 'yesterday'], 'answer': 'They', 'marks': 1},
        {'text': 'Select the correct form: If I ____ you, I would apologize.', 'type': 'mcq', 'options': ['am', 'was', 'were', 'be'], 'answer': 'were', 'marks': 1},
        {'text': 'Which word is a conjunction?', 'type': 'mcq', 'options': ['quickly', 'however', 'beautiful', 'happily'], 'answer': 'however', 'marks': 1},
        # Fill Blank
        {'text': 'The plural of "child" is _______.', 'type': 'fill_blank', 'answer': 'children', 'marks': 1},
        {'text': 'The comparative form of "good" is _______.', 'type': 'fill_blank', 'answer': 'better', 'marks': 1},
        {'text': 'Add the correct punctuation: Its a lovely day', 'type': 'fill_blank', 'answer': "It's a lovely day.", 'marks': 1},
        # Written
        {'text': 'Explain the difference between "their", "there", and "they\'re". Give an example sentence for each.', 'type': 'written', 'answer': 'Their = possessive (their book), There = place (over there), They\'re = they are (they\'re happy)', 'marks': 3},
        {'text': 'Rewrite the following sentence in passive voice: The cat chased the mouse.', 'type': 'written', 'answer': 'The mouse was chased by the cat.', 'marks': 2},
    ],
    'vocabulary': [
        # MCQ
        {'text': 'What does "abundant" mean?', 'type': 'mcq', 'options': ['scarce', 'plentiful', 'tiny', 'dark'], 'answer': 'plentiful', 'marks': 1},
        {'text': 'Choose the antonym of "genuine":', 'type': 'mcq', 'options': ['real', 'authentic', 'fake', 'true'], 'answer': 'fake', 'marks': 1},
        {'text': 'Which word means "to make something clear"?', 'type': 'mcq', 'options': ['confuse', 'clarify', 'complicate', 'conceal'], 'answer': 'clarify', 'marks': 1},
        {'text': '"Enormous" is a synonym for:', 'type': 'mcq', 'options': ['tiny', 'huge', 'average', 'minimal'], 'answer': 'huge', 'marks': 1},
        # Fill Blank
        {'text': 'The opposite of "generous" is _______.', 'type': 'fill_blank', 'answer': 'selfish', 'marks': 1},
        {'text': 'A person who writes books is called an _______.', 'type': 'fill_blank', 'answer': 'author', 'marks': 1},
        # Written
        {'text': 'Use the word "reluctant" in a sentence that shows you understand its meaning.', 'type': 'written', 'answer': 'Example: She was reluctant to speak in front of the class because she felt nervous.', 'marks': 2},
    ],
    'comprehension': [
        # MCQ with reading context
        {'text': 'The old lighthouse stood on the rocky cliff, its beam cutting through the foggy night. What does the lighthouse do?', 'type': 'mcq', 'options': ['Creates fog', 'Shines light through fog', 'Stands on water', 'Hides from ships'], 'answer': 'Shines light through fog', 'marks': 1},
        {'text': 'Maya practiced the piano every day for months. When the recital came, her fingers danced across the keys effortlessly. What can you infer about Maya?', 'type': 'mcq', 'options': ['She never practiced', 'Her hard work paid off', 'She hates piano', 'She played poorly'], 'answer': 'Her hard work paid off', 'marks': 1},
        # Written
        {'text': 'Read: "The rainforest is often called the lungs of the Earth because it produces much of the world\'s oxygen." Why is this comparison made?', 'type': 'written', 'answer': 'Just as lungs help us breathe by processing air, rainforests produce oxygen that the world needs. Both are essential for life.', 'marks': 3},
        {'text': 'Explain why authors use metaphors in their writing. Give an example.', 'type': 'written', 'answer': 'Authors use metaphors to create vivid imagery and help readers understand ideas by comparing them to familiar things. Example: "Time is money" compares time to money to show its value.', 'marks': 3},
    ],
    'spelling': [
        # MCQ
        {'text': 'Which word is spelled correctly?', 'type': 'mcq', 'options': ['recieve', 'receive', 'receve', 'receeve'], 'answer': 'receive', 'marks': 1},
        {'text': 'Choose the correct spelling:', 'type': 'mcq', 'options': ['accomodation', 'accommodation', 'acomodation', 'acommodation'], 'answer': 'accommodation', 'marks': 1},
        {'text': 'Which is spelled correctly?', 'type': 'mcq', 'options': ['occurence', 'occurrence', 'occurrance', 'occurance'], 'answer': 'occurrence', 'marks': 1},
        # Fill Blank
        {'text': 'Correct the spelling: The _______ (neccessary) items are in the bag.', 'type': 'fill_blank', 'answer': 'necessary', 'marks': 1},
        {'text': 'Correct the spelling: She showed great _______ (independance).', 'type': 'fill_blank', 'answer': 'independence', 'marks': 1},
    ],
}

# ============================================================================
# MATHEMATICS QUESTIONS - Cambridge Y6 Level
# Mix of: MCQ, Fill Blank, Written (show working), Calculation
# ============================================================================

MATH_QUESTIONS = {
    'arithmetic': [
        # MCQ
        {'text': 'What is 5 + 9 × 3?', 'type': 'mcq', 'options': ['42', '32', '27', '17'], 'answer': '32', 'marks': 1},
        {'text': 'Calculate: 6 × (4 + 5)', 'type': 'mcq', 'options': ['29', '54', '45', '33'], 'answer': '54', 'marks': 1},
        {'text': 'What is 20% of 150?', 'type': 'mcq', 'options': ['20', '25', '30', '35'], 'answer': '30', 'marks': 1},
        {'text': 'Round 7.846 to 2 decimal places:', 'type': 'mcq', 'options': ['7.84', '7.85', '7.80', '7.90'], 'answer': '7.85', 'marks': 1},
        # Fill Blank
        {'text': 'Calculate: 456 + 789 = _______', 'type': 'fill_blank', 'answer': '1245', 'marks': 1},
        {'text': 'What is 1000 - 347?', 'type': 'fill_blank', 'answer': '653', 'marks': 1},
        {'text': 'Calculate: 25 × 12 = _______', 'type': 'fill_blank', 'answer': '300', 'marks': 1},
        {'text': 'What is 144 ÷ 12?', 'type': 'fill_blank', 'answer': '12', 'marks': 1},
        {'text': 'Calculate: 3.5 + 2.7 = _______', 'type': 'fill_blank', 'answer': '6.2', 'marks': 1},
        # Written
        {'text': 'Show your working: A shop sells pencils at RM0.80 each. How much do 15 pencils cost?', 'type': 'written', 'answer': '15 × RM0.80 = RM12.00', 'marks': 2},
    ],
    'fractions': [
        # MCQ
        {'text': 'What is 1/2 + 1/4?', 'type': 'mcq', 'options': ['2/6', '3/4', '1/6', '2/4'], 'answer': '3/4', 'marks': 1},
        {'text': 'Simplify: 12/18', 'type': 'mcq', 'options': ['4/6', '2/3', '6/9', '3/4'], 'answer': '2/3', 'marks': 1},
        {'text': 'Convert 0.75 to a fraction in simplest form:', 'type': 'mcq', 'options': ['75/100', '3/4', '7/5', '15/20'], 'answer': '3/4', 'marks': 1},
        {'text': 'What is 3/5 of 40?', 'type': 'mcq', 'options': ['20', '24', '25', '30'], 'answer': '24', 'marks': 1},
        # Fill Blank
        {'text': 'Express 2/5 as a decimal: _______', 'type': 'fill_blank', 'answer': '0.4', 'marks': 1},
        {'text': 'What is 1/3 + 1/6 = _______ (as a fraction)', 'type': 'fill_blank', 'answer': '1/2', 'marks': 1},
        # Written
        {'text': 'Show your working: Sara ate 2/5 of a pizza. Her brother ate 1/4 of the same pizza. How much pizza did they eat together?', 'type': 'written', 'answer': '2/5 + 1/4 = 8/20 + 5/20 = 13/20 of the pizza', 'marks': 3},
    ],
    'geometry': [
        # MCQ
        {'text': 'What is the area of a rectangle with length 8cm and width 5cm?', 'type': 'mcq', 'options': ['13cm²', '40cm²', '26cm²', '80cm²'], 'answer': '40cm²', 'marks': 1},
        {'text': 'How many sides does a hexagon have?', 'type': 'mcq', 'options': ['5', '6', '7', '8'], 'answer': '6', 'marks': 1},
        {'text': 'The angles of a triangle add up to:', 'type': 'mcq', 'options': ['90°', '180°', '270°', '360°'], 'answer': '180°', 'marks': 1},
        {'text': 'What type of angle is 135°?', 'type': 'mcq', 'options': ['Acute', 'Right', 'Obtuse', 'Reflex'], 'answer': 'Obtuse', 'marks': 1},
        # Fill Blank
        {'text': 'The perimeter of a square with side 7cm is _______ cm.', 'type': 'fill_blank', 'answer': '28', 'marks': 1},
        {'text': 'A triangle has angles of 60° and 80°. The third angle is _______ degrees.', 'type': 'fill_blank', 'answer': '40', 'marks': 1},
        # Written
        {'text': 'Calculate the area of a triangle with base 10cm and height 6cm. Show your working.', 'type': 'written', 'answer': 'Area = 1/2 × base × height = 1/2 × 10 × 6 = 30cm²', 'marks': 2},
        {'text': 'A circle has a radius of 7cm. Calculate its circumference using π = 22/7.', 'type': 'written', 'answer': 'Circumference = 2πr = 2 × 22/7 × 7 = 44cm', 'marks': 2},
    ],
    'word_problems': [
        # Fill Blank
        {'text': 'Sarah has 48 stickers. She gives 1/4 to her friend. How many stickers does she give away?', 'type': 'fill_blank', 'answer': '12', 'marks': 1},
        {'text': 'A train travels at 80km/h. How far does it travel in 3 hours?', 'type': 'fill_blank', 'answer': '240', 'marks': 1},
        # Written
        {'text': 'A bookshop sells books at RM25 each. If they offer a 20% discount, how much would 3 books cost? Show your working.', 'type': 'written', 'answer': 'Discounted price = RM25 × 0.8 = RM20. Total = RM20 × 3 = RM60', 'marks': 3},
        {'text': 'A tank can hold 500 liters of water. It is 3/5 full. How many more liters are needed to fill it?', 'type': 'written', 'answer': 'Water in tank = 500 × 3/5 = 300L. Space remaining = 500 - 300 = 200 liters', 'marks': 3},
        {'text': 'The ratio of boys to girls in a class is 3:2. If there are 15 boys, how many girls are there?', 'type': 'written', 'answer': 'Boys:Girls = 3:2. If 3 parts = 15, then 1 part = 5. Girls = 2 × 5 = 10', 'marks': 2},
    ],
    'data_handling': [
        # MCQ
        {'text': 'The mean of 4, 8, 6, 10, 12 is:', 'type': 'mcq', 'options': ['6', '8', '10', '12'], 'answer': '8', 'marks': 1},
        {'text': 'What is the mode of: 3, 5, 7, 5, 9, 5, 2?', 'type': 'mcq', 'options': ['3', '5', '7', '9'], 'answer': '5', 'marks': 1},
        {'text': 'The range of 15, 23, 8, 31, 12 is:', 'type': 'mcq', 'options': ['15', '23', '31', '23'], 'answer': '23', 'marks': 1},
        # Fill Blank
        {'text': 'Find the median of: 2, 5, 8, 11, 14. The median is _______.', 'type': 'fill_blank', 'answer': '8', 'marks': 1},
    ],
}

# ============================================================================
# SCIENCE QUESTIONS - Cambridge Y6 Level
# Mix of: MCQ, Fill Blank, Written, Matching, Labeling (with images)
# ============================================================================

SCIENCE_QUESTIONS = {
    'biology': [
        # MCQ
        {'text': 'What is the main function of the heart?', 'type': 'mcq', 'options': ['Digest food', 'Pump blood around the body', 'Filter waste', 'Store oxygen'], 'answer': 'Pump blood around the body', 'marks': 1},
        {'text': 'Which part of the plant absorbs water from the soil?', 'type': 'mcq', 'options': ['Leaves', 'Stem', 'Roots', 'Flowers'], 'answer': 'Roots', 'marks': 1},
        {'text': 'What do plants produce during photosynthesis?', 'type': 'mcq', 'options': ['Carbon dioxide', 'Oxygen and glucose', 'Nitrogen', 'Water only'], 'answer': 'Oxygen and glucose', 'marks': 1},
        {'text': 'Which organ is part of the digestive system?', 'type': 'mcq', 'options': ['Heart', 'Lungs', 'Stomach', 'Brain'], 'answer': 'Stomach', 'marks': 1},
        {'text': 'What is the largest organ in the human body?', 'type': 'mcq', 'options': ['Heart', 'Brain', 'Skin', 'Liver'], 'answer': 'Skin', 'marks': 1},
        # Fill Blank
        {'text': 'The process by which plants make food using sunlight is called _______.', 'type': 'fill_blank', 'answer': 'photosynthesis', 'marks': 1},
        {'text': 'The organ that pumps blood around the body is the _______.', 'type': 'fill_blank', 'answer': 'heart', 'marks': 1},
        {'text': 'Oxygen enters the body through the _______.', 'type': 'fill_blank', 'answer': 'lungs', 'marks': 1},
        # Written
        {'text': 'Explain why plants are important for life on Earth. Give two reasons.', 'type': 'written', 'answer': '1. Plants produce oxygen through photosynthesis which animals need to breathe. 2. Plants provide food for animals and humans in the food chain.', 'marks': 4},
        {'text': 'Describe the path of blood through the heart and lungs.', 'type': 'written', 'answer': 'Deoxygenated blood enters the right atrium, moves to right ventricle, goes to lungs to get oxygen, returns to left atrium, moves to left ventricle, and is pumped to the body.', 'marks': 4},
        # Matching
        {'text': 'Match the organ to its function', 'type': 'matching', 'matching_pairs': [{'left': 'Heart', 'right': 'Pumps blood'}, {'left': 'Lungs', 'right': 'Gas exchange'}, {'left': 'Stomach', 'right': 'Digests food'}, {'left': 'Brain', 'right': 'Controls body'}], 'answer': 'Heart-Pumps blood, Lungs-Gas exchange, Stomach-Digests food, Brain-Controls body', 'marks': 4},
    ],
    'physics': [
        # MCQ
        {'text': 'What force pulls objects towards the Earth?', 'type': 'mcq', 'options': ['Friction', 'Gravity', 'Magnetism', 'Air resistance'], 'answer': 'Gravity', 'marks': 1},
        {'text': 'Which type of energy does a moving car have?', 'type': 'mcq', 'options': ['Potential energy', 'Kinetic energy', 'Sound energy', 'Nuclear energy'], 'answer': 'Kinetic energy', 'marks': 1},
        {'text': 'What travels faster: sound or light?', 'type': 'mcq', 'options': ['Sound', 'Light', 'They travel equally', 'Neither moves'], 'answer': 'Light', 'marks': 1},
        {'text': 'Which is an example of a conductor of electricity?', 'type': 'mcq', 'options': ['Rubber', 'Plastic', 'Copper', 'Wood'], 'answer': 'Copper', 'marks': 1},
        {'text': 'What is the unit of force?', 'type': 'mcq', 'options': ['Meter', 'Newton', 'Kilogram', 'Joule'], 'answer': 'Newton', 'marks': 1},
        # Fill Blank
        {'text': 'The speed of light is approximately _______ km/s.', 'type': 'fill_blank', 'answer': '300000', 'marks': 1},
        {'text': 'A material that does not allow electricity to pass through is called an _______.', 'type': 'fill_blank', 'answer': 'insulator', 'marks': 1},
        # Written
        {'text': 'Explain the difference between potential energy and kinetic energy. Give an example of each.', 'type': 'written', 'answer': 'Potential energy is stored energy (e.g., a ball held up high). Kinetic energy is energy of motion (e.g., a rolling ball).', 'marks': 4},
        {'text': 'Why does a parachute slow down a falling object?', 'type': 'written', 'answer': 'A parachute increases air resistance/drag, which opposes the force of gravity, causing the object to fall more slowly.', 'marks': 3},
    ],
    'chemistry': [
        # MCQ
        {'text': 'What are the three states of matter?', 'type': 'mcq', 'options': ['Hot, cold, warm', 'Solid, liquid, gas', 'Hard, soft, fluid', 'Heavy, light, medium'], 'answer': 'Solid, liquid, gas', 'marks': 1},
        {'text': 'At what temperature does water boil at sea level?', 'type': 'mcq', 'options': ['0°C', '50°C', '100°C', '212°C'], 'answer': '100°C', 'marks': 1},
        {'text': 'Which gas do we breathe in?', 'type': 'mcq', 'options': ['Carbon dioxide', 'Nitrogen', 'Oxygen', 'Hydrogen'], 'answer': 'Oxygen', 'marks': 1},
        {'text': 'What happens when ice is heated?', 'type': 'mcq', 'options': ['It stays the same', 'It melts into water', 'It becomes gas directly', 'It gets harder'], 'answer': 'It melts into water', 'marks': 1},
        # Fill Blank
        {'text': 'The chemical symbol for water is _______.', 'type': 'fill_blank', 'answer': 'H2O', 'marks': 1},
        {'text': 'The gas we breathe out is _______ dioxide.', 'type': 'fill_blank', 'answer': 'carbon', 'marks': 1},
        {'text': 'When a liquid changes to a gas, it is called _______.', 'type': 'fill_blank', 'answer': 'evaporation', 'marks': 1},
        # Written
        {'text': 'Explain the difference between a physical change and a chemical change. Give an example of each.', 'type': 'written', 'answer': 'Physical change: substance changes form but remains the same material (e.g., ice melting to water). Chemical change: new substances are formed (e.g., burning wood produces ash and smoke).', 'marks': 4},
    ],
    'earth_science': [
        # MCQ
        {'text': 'What causes day and night?', 'type': 'mcq', 'options': ['Moon orbiting Earth', 'Earth rotating on its axis', 'Sun moving around Earth', 'Clouds blocking sunlight'], 'answer': 'Earth rotating on its axis', 'marks': 1},
        {'text': 'Which layer of Earth is the hottest?', 'type': 'mcq', 'options': ['Crust', 'Mantle', 'Outer core', 'Inner core'], 'answer': 'Inner core', 'marks': 1},
        {'text': 'What type of rock is formed from cooled lava?', 'type': 'mcq', 'options': ['Sedimentary', 'Metamorphic', 'Igneous', 'Limestone'], 'answer': 'Igneous', 'marks': 1},
        # Fill Blank
        {'text': 'The Earth takes _______ days to orbit the Sun.', 'type': 'fill_blank', 'answer': '365', 'marks': 1},
        {'text': 'The movement of tectonic plates can cause _______.', 'type': 'fill_blank', 'answer': 'earthquakes', 'marks': 1},
        # Written
        {'text': 'Explain how the water cycle works. Include at least 3 stages.', 'type': 'written', 'answer': '1. Evaporation: Sun heats water from oceans/lakes, turning it into water vapor. 2. Condensation: Water vapor rises, cools, and forms clouds. 3. Precipitation: Water falls as rain or snow. 4. Collection: Water returns to oceans, lakes, or groundwater.', 'marks': 4},
    ],
}

# ============================================================================
# ICT QUESTIONS - Cambridge Y6 Level
# Mix of: MCQ, Fill Blank, Written, Matching, Drawing
# With Educational Images
# ============================================================================

ICT_QUESTIONS = {
    'hardware': [
        # MCQ
        {'text': 'Which device is used to display information on a screen?', 'type': 'mcq', 'options': ['Keyboard', 'Mouse', 'Monitor', 'Speaker'], 'answer': 'Monitor', 'marks': 1},
        {'text': 'Which of these is an input device?', 'type': 'mcq', 'options': ['Printer', 'Speaker', 'Keyboard', 'Monitor'], 'answer': 'Keyboard', 'marks': 1},
        {'text': 'What is the main function of RAM?', 'type': 'mcq', 'options': ['Store files permanently', 'Temporary memory for running programs', 'Connect to the internet', 'Display graphics'], 'answer': 'Temporary memory for running programs', 'marks': 1},
        {'text': 'Which device converts printed documents into digital format?', 'type': 'mcq', 'options': ['Printer', 'Scanner', 'Webcam', 'Microphone'], 'answer': 'Scanner', 'marks': 1},
        {'text': 'Which is an output device?', 'type': 'mcq', 'options': ['Mouse', 'Keyboard', 'Scanner', 'Printer'], 'answer': 'Printer', 'marks': 1},
        {'text': 'What does the CPU do?', 'type': 'mcq', 'options': ['Stores data permanently', 'Processes instructions', 'Displays images', 'Prints documents'], 'answer': 'Processes instructions', 'marks': 1},
        {'text': 'Which storage device can hold the most data?', 'type': 'mcq', 'options': ['CD', 'Floppy disk', 'Hard drive', 'USB stick (4GB)'], 'answer': 'Hard drive', 'marks': 1},
        {'text': 'What is a touchscreen?', 'type': 'mcq', 'options': ['Only input device', 'Only output device', 'Both input and output device', 'Storage device'], 'answer': 'Both input and output device', 'marks': 1},
        # Fill Blank
        {'text': 'CPU stands for _______ Processing Unit.', 'type': 'fill_blank', 'answer': 'Central', 'marks': 1},
        {'text': 'RAM stands for Random _______ Memory.', 'type': 'fill_blank', 'answer': 'Access', 'marks': 1},
        {'text': 'A device that produces sound output is called a _______.', 'type': 'fill_blank', 'answer': 'speaker', 'marks': 1},
        {'text': 'USB stands for Universal _______ Bus.', 'type': 'fill_blank', 'answer': 'Serial', 'marks': 1},
        {'text': 'The brain of the computer is the _______.', 'type': 'fill_blank', 'answer': 'CPU', 'marks': 1},
        # Written
        {'text': 'Explain the difference between RAM and ROM.', 'type': 'written', 'answer': 'RAM (Random Access Memory) is temporary memory that loses data when powered off. ROM (Read Only Memory) is permanent memory that keeps data even when powered off.', 'marks': 3},
        {'text': 'Give three examples of input devices and explain what each does.', 'type': 'written', 'answer': '1. Keyboard - allows typing text. 2. Mouse - allows pointing and clicking. 3. Microphone - allows recording sound.', 'marks': 3},
        # Matching
        {'text': 'Match the device to its type', 'type': 'matching', 'matching_pairs': [{'left': 'Keyboard', 'right': 'Input'}, {'left': 'Monitor', 'right': 'Output'}, {'left': 'Hard Drive', 'right': 'Storage'}, {'left': 'Mouse', 'right': 'Input'}], 'answer': 'Keyboard-Input, Monitor-Output, Hard Drive-Storage, Mouse-Input', 'marks': 4},
        # Drawing
        {'text': 'Draw and label a simple computer system showing: Monitor, CPU (System Unit), Keyboard, and Mouse.', 'type': 'drawing', 'answer': 'Drawing showing monitor, CPU unit, keyboard, and mouse with labels', 'drawing_template': {'type': 'freehand', 'instructions': 'Draw a computer setup with 4 components labeled'}, 'marks': 4},
        {'text': 'Draw lines to connect each input device to the correct computer port.', 'type': 'drawing', 'answer': 'Lines connecting devices to appropriate ports', 'drawing_template': {'type': 'connect', 'instructions': 'Match devices to ports'}, 'marks': 3},
    ],
    'software': [
        # MCQ
        {'text': 'What type of software is Microsoft Word?', 'type': 'mcq', 'options': ['Operating system', 'Word processor', 'Web browser', 'Game'], 'answer': 'Word processor', 'marks': 1},
        {'text': 'Which is an example of an operating system?', 'type': 'mcq', 'options': ['Google Chrome', 'Microsoft Word', 'Windows', 'Photoshop'], 'answer': 'Windows', 'marks': 1},
        {'text': 'What is a web browser used for?', 'type': 'mcq', 'options': ['Create documents', 'View websites', 'Edit photos', 'Play games only'], 'answer': 'View websites', 'marks': 1},
        {'text': 'Which software would you use to create a presentation?', 'type': 'mcq', 'options': ['Excel', 'Word', 'PowerPoint', 'Paint'], 'answer': 'PowerPoint', 'marks': 1},
        {'text': 'What does antivirus software do?', 'type': 'mcq', 'options': ['Makes computer faster', 'Protects from malware', 'Creates documents', 'Plays music'], 'answer': 'Protects from malware', 'marks': 1},
        {'text': 'A spreadsheet software is used to:', 'type': 'mcq', 'options': ['Write letters', 'Organize data in rows and columns', 'Draw pictures', 'Play videos'], 'answer': 'Organize data in rows and columns', 'marks': 1},
        {'text': 'Which is NOT an operating system?', 'type': 'mcq', 'options': ['Windows', 'macOS', 'Linux', 'Microsoft Office'], 'answer': 'Microsoft Office', 'marks': 1},
        {'text': 'Which software helps edit photos?', 'type': 'mcq', 'options': ['Notepad', 'Calculator', 'Photoshop', 'VLC'], 'answer': 'Photoshop', 'marks': 1},
        # Fill Blank
        {'text': 'The software that controls all computer hardware is called the _______ system.', 'type': 'fill_blank', 'answer': 'operating', 'marks': 1},
        {'text': 'Microsoft Excel is a _______ application.', 'type': 'fill_blank', 'answer': 'spreadsheet', 'marks': 1},
        {'text': 'A _______ is a program that lets you view websites.', 'type': 'fill_blank', 'answer': 'browser', 'marks': 1},
        {'text': 'Software that is free to use is called _______ software.', 'type': 'fill_blank', 'answer': 'freeware', 'marks': 1},
        # Written
        {'text': 'Explain the difference between system software and application software. Give one example of each.', 'type': 'written', 'answer': 'System software (e.g., Windows) controls hardware and runs the computer. Application software (e.g., Word) helps users do specific tasks like writing documents.', 'marks': 3},
        {'text': 'Why is it important to update your operating system regularly?', 'type': 'written', 'answer': 'Updates fix security problems, add new features, improve performance, and fix bugs that could cause the computer to malfunction.', 'marks': 3},
        # Matching
        {'text': 'Match the software to its purpose', 'type': 'matching', 'matching_pairs': [{'left': 'Word', 'right': 'Writing documents'}, {'left': 'Excel', 'right': 'Making spreadsheets'}, {'left': 'PowerPoint', 'right': 'Creating presentations'}, {'left': 'Paint', 'right': 'Drawing pictures'}], 'answer': 'Word-Writing documents, Excel-Making spreadsheets, PowerPoint-Creating presentations, Paint-Drawing pictures', 'marks': 4},
    ],
    'programming': [
        # MCQ
        {'text': 'What is a variable in programming?', 'type': 'mcq', 'options': ['A fixed number', 'A container that stores data', 'A type of loop', 'A hardware part'], 'answer': 'A container that stores data', 'marks': 1},
        {'text': 'Which structure repeats a block of code multiple times?', 'type': 'mcq', 'options': ['Selection', 'Loop', 'Sequence', 'Variable'], 'answer': 'Loop', 'marks': 1},
        {'text': 'What does the IF statement check?', 'type': 'mcq', 'options': ['A condition', 'A variable name', 'A file', 'A website'], 'answer': 'A condition', 'marks': 1},
        {'text': 'In Scratch, which block makes a sprite move?', 'type': 'mcq', 'options': ['say', 'move', 'wait', 'ask'], 'answer': 'move', 'marks': 1},
        {'text': 'What is an algorithm?', 'type': 'mcq', 'options': ['A type of computer', 'Step-by-step instructions', 'A programming language', 'A website'], 'answer': 'Step-by-step instructions', 'marks': 1},
        {'text': 'What symbol is used for a decision in a flowchart?', 'type': 'mcq', 'options': ['Rectangle', 'Diamond', 'Oval', 'Circle'], 'answer': 'Diamond', 'marks': 1},
        # Fill Blank
        {'text': 'A set of step-by-step instructions to solve a problem is called an _______.', 'type': 'fill_blank', 'answer': 'algorithm', 'marks': 1},
        {'text': 'A _______ is used to repeat code until a condition is met.', 'type': 'fill_blank', 'answer': 'loop', 'marks': 1},
        {'text': 'The flowchart symbol for start and end is an _______.', 'type': 'fill_blank', 'answer': 'oval', 'marks': 1},
        # Written
        {'text': 'Write an algorithm (step-by-step instructions) for brushing your teeth.', 'type': 'written', 'answer': '1. Pick up toothbrush. 2. Put toothpaste on brush. 3. Wet the brush. 4. Brush teeth for 2 minutes. 5. Rinse mouth. 6. Put brush away.', 'marks': 4},
        {'text': 'Explain why planning with a flowchart is important before writing code.', 'type': 'written', 'answer': 'Flowcharts help visualize the logic, identify errors early, make code easier to write, and help others understand your plan.', 'marks': 3},
        {'text': 'What is the difference between a sequence and a loop in programming?', 'type': 'written', 'answer': 'A sequence runs instructions one after another in order. A loop repeats instructions multiple times until a condition is met.', 'marks': 3},
        # Drawing
        {'text': 'Draw a flowchart for deciding if a number is positive or negative.', 'type': 'drawing', 'answer': 'Flowchart with Start, Input number, Decision (>0?), Output positive/negative, End', 'drawing_template': {'type': 'flowchart', 'instructions': 'Use oval for start/end, diamond for decision, rectangle for process'}, 'marks': 5},
        {'text': 'Draw a flowchart showing the steps to make a cup of tea.', 'type': 'drawing', 'answer': 'Flowchart with Start, Boil water, Add tea bag, Pour water, Wait, Remove tea bag, End', 'drawing_template': {'type': 'flowchart', 'instructions': 'Draw the process in order with correct symbols'}, 'marks': 5},
        {'text': 'Complete the missing decision box in this flowchart for checking if someone can vote (age >= 18).', 'type': 'drawing', 'answer': 'Decision diamond with "Age >= 18?" and Yes/No branches', 'drawing_template': {'type': 'flowchart', 'instructions': 'Fill in the missing decision'}, 'marks': 3},
    ],
    'internet_safety': [
        # MCQ
        {'text': 'What does WWW stand for?', 'type': 'mcq', 'options': ['World Wide Web', 'Wide World Web', 'World Web Wide', 'Web World Wide'], 'answer': 'World Wide Web', 'marks': 1},
        {'text': 'Which is a safe password practice?', 'type': 'mcq', 'options': ['Use "password123"', 'Share with friends', 'Use mix of letters, numbers, symbols', 'Use your birthday'], 'answer': 'Use mix of letters, numbers, symbols', 'marks': 1},
        {'text': 'What should you do if a stranger online asks for your address?', 'type': 'mcq', 'options': ['Give it to them', 'Ask your parents first', 'Never share and tell an adult', 'Share if they seem nice'], 'answer': 'Never share and tell an adult', 'marks': 1},
        {'text': 'What is phishing?', 'type': 'mcq', 'options': ['A fishing game', 'Trick emails to steal information', 'A type of website', 'A search engine'], 'answer': 'Trick emails to steal information', 'marks': 1},
        {'text': 'Which is a search engine?', 'type': 'mcq', 'options': ['Facebook', 'Google', 'WhatsApp', 'Word'], 'answer': 'Google', 'marks': 1},
        {'text': 'What does the lock icon in a browser address bar mean?', 'type': 'mcq', 'options': ['Site is blocked', 'Connection is secure', 'Site is slow', 'You cannot use the site'], 'answer': 'Connection is secure', 'marks': 1},
        {'text': 'Which is personal information you should NOT share online?', 'type': 'mcq', 'options': ['Your favorite color', 'Your home address', 'Your favorite book', 'The weather'], 'answer': 'Your home address', 'marks': 1},
        {'text': 'What is cyberbullying?', 'type': 'mcq', 'options': ['Playing games online', 'Sending mean messages online', 'Using the internet', 'Watching videos'], 'answer': 'Sending mean messages online', 'marks': 1},
        # Fill Blank
        {'text': 'URL stands for Uniform Resource _______.', 'type': 'fill_blank', 'answer': 'Locator', 'marks': 1},
        {'text': 'Unwanted commercial email is called _______.', 'type': 'fill_blank', 'answer': 'spam', 'marks': 1},
        {'text': 'Software that damages computers is called _______.', 'type': 'fill_blank', 'answer': 'malware', 'marks': 1},
        {'text': 'A program that protects your computer from viruses is called _______ software.', 'type': 'fill_blank', 'answer': 'antivirus', 'marks': 1},
        {'text': 'HTTP stands for HyperText Transfer _______.', 'type': 'fill_blank', 'answer': 'Protocol', 'marks': 1},
        # Written
        {'text': 'List 3 rules for staying safe online.', 'type': 'written', 'answer': '1. Never share personal information. 2. Use strong passwords. 3. Tell an adult if something makes you uncomfortable. 4. Only visit trusted websites.', 'marks': 3},
        {'text': 'Explain why you should not click on links in emails from unknown senders.', 'type': 'written', 'answer': 'Unknown links may contain viruses, lead to fake websites, or try to steal your personal information through phishing attacks.', 'marks': 3},
        {'text': 'What should you do if you see cyberbullying online?', 'type': 'written', 'answer': 'Do not respond, take screenshots as evidence, block the person, report it to the platform, and tell a trusted adult.', 'marks': 3},
        # Matching
        {'text': 'Match the internet term to its meaning', 'type': 'matching', 'matching_pairs': [{'left': 'Browser', 'right': 'Views websites'}, {'left': 'Email', 'right': 'Electronic mail'}, {'left': 'Password', 'right': 'Secret code to login'}, {'left': 'Download', 'right': 'Get files from internet'}], 'answer': 'Browser-Views websites, Email-Electronic mail, Password-Secret code to login, Download-Get files from internet', 'marks': 4},
    ],
    'data_spreadsheets': [
        # MCQ
        {'text': 'In Excel, what is a cell?', 'type': 'mcq', 'options': ['A row', 'A column', 'The intersection of a row and column', 'A formula'], 'answer': 'The intersection of a row and column', 'marks': 1},
        {'text': 'Which function adds up numbers in Excel?', 'type': 'mcq', 'options': ['AVERAGE', 'COUNT', 'SUM', 'MAX'], 'answer': 'SUM', 'marks': 1},
        {'text': 'Cell A1 means:', 'type': 'mcq', 'options': ['First row, first column', 'Column A, Row 1', 'First page', 'First table'], 'answer': 'Column A, Row 1', 'marks': 1},
        {'text': 'What symbol do formulas in Excel start with?', 'type': 'mcq', 'options': ['#', '$', '=', '@'], 'answer': '=', 'marks': 1},
        {'text': 'Which chart type is best for showing parts of a whole?', 'type': 'mcq', 'options': ['Line chart', 'Bar chart', 'Pie chart', 'Scatter plot'], 'answer': 'Pie chart', 'marks': 1},
        {'text': 'What does the AVERAGE function do?', 'type': 'mcq', 'options': ['Finds the total', 'Finds the middle value', 'Finds the mean', 'Counts cells'], 'answer': 'Finds the mean', 'marks': 1},
        # Fill Blank
        {'text': 'The formula =A1+B1 will _______ the values in cells A1 and B1.', 'type': 'fill_blank', 'answer': 'add', 'marks': 1},
        {'text': 'To find the highest value, you use the _______ function.', 'type': 'fill_blank', 'answer': 'MAX', 'marks': 1},
        {'text': 'Columns in a spreadsheet are labeled with _______.', 'type': 'fill_blank', 'answer': 'letters', 'marks': 1},
        {'text': 'Rows in a spreadsheet are labeled with _______.', 'type': 'fill_blank', 'answer': 'numbers', 'marks': 1},
        # Written
        {'text': 'Write the formula to add the values in cells B2, B3, B4, and B5.', 'type': 'written', 'answer': '=SUM(B2:B5) or =B2+B3+B4+B5', 'marks': 2},
        {'text': 'Explain when you would use a bar chart instead of a line chart.', 'type': 'written', 'answer': 'Bar charts are used to compare different categories or groups. Line charts are used to show changes over time.', 'marks': 3},
        {'text': 'A shop sells items at these prices: RM5, RM8, RM12, RM15. Write the formula to find the average price.', 'type': 'written', 'answer': '=AVERAGE(A1:A4) if prices are in cells A1 to A4, which equals RM10', 'marks': 2},
        # Matching
        {'text': 'Match the function to what it does', 'type': 'matching', 'matching_pairs': [{'left': 'SUM', 'right': 'Adds numbers'}, {'left': 'AVERAGE', 'right': 'Finds mean'}, {'left': 'MAX', 'right': 'Finds highest'}, {'left': 'MIN', 'right': 'Finds lowest'}], 'answer': 'SUM-Adds numbers, AVERAGE-Finds mean, MAX-Finds highest, MIN-Finds lowest', 'marks': 4},
    ],
    'networks': [
        # MCQ
        {'text': 'What does LAN stand for?', 'type': 'mcq', 'options': ['Large Area Network', 'Local Area Network', 'Long Area Network', 'Linked Area Network'], 'answer': 'Local Area Network', 'marks': 1},
        {'text': 'Which device connects a computer to the internet?', 'type': 'mcq', 'options': ['Monitor', 'Keyboard', 'Router', 'Speaker'], 'answer': 'Router', 'marks': 1},
        {'text': 'What is WiFi?', 'type': 'mcq', 'options': ['A cable connection', 'Wireless internet connection', 'A computer brand', 'A type of software'], 'answer': 'Wireless internet connection', 'marks': 1},
        {'text': 'What does WAN stand for?', 'type': 'mcq', 'options': ['Wide Area Network', 'Wireless Area Network', 'Web Area Network', 'World Area Network'], 'answer': 'Wide Area Network', 'marks': 1},
        {'text': 'A network of computers within a school is called:', 'type': 'mcq', 'options': ['WAN', 'LAN', 'MAN', 'Internet'], 'answer': 'LAN', 'marks': 1},
        # Fill Blank
        {'text': 'A _______ connects devices in a network and directs data traffic.', 'type': 'fill_blank', 'answer': 'router', 'marks': 1},
        {'text': 'The worldwide network of computers is called the _______.', 'type': 'fill_blank', 'answer': 'internet', 'marks': 1},
        {'text': 'A computer that provides services to other computers is called a _______.', 'type': 'fill_blank', 'answer': 'server', 'marks': 1},
        # Written
        {'text': 'Explain the difference between LAN and WAN.', 'type': 'written', 'answer': 'LAN (Local Area Network) covers a small area like a school or home. WAN (Wide Area Network) covers large areas, even countries. The internet is the largest WAN.', 'marks': 3},
        {'text': 'Give two advantages of using a computer network in a school.', 'type': 'written', 'answer': '1. Share files and resources easily. 2. Share printers and internet connection. 3. Communicate through email. 4. Central storage and backup.', 'marks': 3},
        # Drawing
        {'text': 'Draw a simple network diagram showing 4 computers connected to a router.', 'type': 'drawing', 'answer': 'Diagram with router in center and 4 computers connected to it', 'drawing_template': {'type': 'freehand', 'instructions': 'Draw a star topology with router in center'}, 'marks': 4},
        # Matching
        {'text': 'Match the network device to its function', 'type': 'matching', 'matching_pairs': [{'left': 'Router', 'right': 'Connects networks'}, {'left': 'Switch', 'right': 'Connects devices in LAN'}, {'left': 'Modem', 'right': 'Converts signals'}, {'left': 'Server', 'right': 'Stores and shares data'}], 'answer': 'Router-Connects networks, Switch-Connects devices in LAN, Modem-Converts signals, Server-Stores and shares data', 'marks': 4},
    ],
}

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def generate_question_set_title(subject_id, topic, set_number):
    """Generate a realistic question set title"""
    titles = {
        1: [f"English Language Practice {set_number}", f"Reading & Writing Skills {set_number}",
            f"Grammar & Vocabulary {set_number}", f"English Comprehension {set_number}",
            f"Language Arts Test {set_number}"],
        2: [f"Mathematics Practice {set_number}", f"Problem Solving Challenge {set_number}",
            f"Arithmetic & Geometry {set_number}", f"Math Skills Assessment {set_number}",
            f"Number Operations {set_number}"],
        3: [f"ICT Knowledge Test {set_number}", f"Computer Literacy {set_number}",
            f"Digital Skills Assessment {set_number}", f"Programming & Computing {set_number}",
            f"Technology Fundamentals {set_number}"],
        4: [f"Science Discovery {set_number}", f"Nature & Science {set_number}",
            f"Science Explorer {set_number}", f"Scientific Investigation {set_number}",
            f"Biology & Physics {set_number}"]
    }
    return random.choice(titles.get(subject_id, [f"Practice Test {set_number}"]))


def get_mixed_questions_for_subject(subject_id, num_questions=12):
    """Get a MIX of different question types for a subject"""
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
            q_copy = q.copy()
            q_copy['topic'] = topic
            all_questions.append(q_copy)

    # Ensure we get a MIX of question types
    types_available = list(set(q['type'] for q in all_questions))
    selected = []

    # First, ensure at least one of each type (if available)
    for qtype in types_available:
        type_questions = [q for q in all_questions if q['type'] == qtype]
        if type_questions and len(selected) < num_questions:
            selected.append(random.choice(type_questions))

    # Fill remaining with random questions (avoiding duplicates)
    remaining = [q for q in all_questions if q not in selected]
    random.shuffle(remaining)

    while len(selected) < num_questions and remaining:
        selected.append(remaining.pop())

    random.shuffle(selected)
    return selected[:num_questions]


def clear_all_questions():
    """Delete all existing questions, question sets, and related data"""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        print("Clearing existing data...")

        # Delete in order due to foreign keys
        cursor.execute("DELETE FROM student_answers")
        print("  - Cleared student_answers")

        cursor.execute("DELETE FROM practice_exams")
        print("  - Cleared practice_exams")

        cursor.execute("DELETE FROM questions")
        print("  - Cleared questions")

        cursor.execute("DELETE FROM question_sets")
        print("  - Cleared question_sets")

        conn.commit()
        print("All question data cleared successfully!")

    except Exception as e:
        conn.rollback()
        print(f"Error clearing data: {e}")
        raise
    finally:
        cursor.close()
        conn.close()


def seed_admin_user():
    """Create admin user if not exists"""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
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
    """Create student user (Rifah) if not exists"""
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


def seed_question_sets(sets_per_subject=10):
    """Seed question sets with mixed question types for all subjects"""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    subjects = [
        (1, 'English'),
        (2, 'Mathematics'),
        (3, 'ICT'),
        (4, 'Science')
    ]

    total_sets = 0
    total_questions = 0

    try:
        for subject_id, subject_name in subjects:
            print(f"\nSeeding {subject_name} question sets...")

            for i in range(1, sets_per_subject + 1):
                # Create question set
                title = generate_question_set_title(subject_id, None, i)
                num_questions = random.randint(10, 15)
                difficulty = random.choice(['easy', 'medium', 'hard'])
                duration = random.choice([30, 45, 60])

                # Get mixed questions
                questions = get_mixed_questions_for_subject(subject_id, num_questions)

                # Calculate total marks from actual questions
                total_marks = sum(q.get('marks', 1) for q in questions)

                cursor.execute("""
                    INSERT INTO question_sets (subject_id, title, total_marks, duration_minutes, difficulty)
                    VALUES (%s, %s, %s, %s, %s)
                """, (subject_id, title, total_marks, duration, difficulty))

                question_set_id = cursor.lastrowid

                # Add questions with their respective types
                for q_num, q in enumerate(questions, 1):
                    marks = q.get('marks', 1)
                    options_json = json.dumps(q.get('options')) if q.get('options') else None
                    matching_json = json.dumps(q.get('matching_pairs')) if q.get('matching_pairs') else None
                    drawing_template_json = json.dumps(q.get('drawing_template')) if q.get('drawing_template') else None
                    image_url = q.get('image_url')

                    cursor.execute("""
                        INSERT INTO questions
                        (question_set_id, question_number, question_type, question_text,
                         marks, correct_answer, options, matching_pairs, drawing_template, image_url)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (question_set_id, q_num, q['type'], q['text'],
                          marks, q['answer'], options_json, matching_json, drawing_template_json, image_url))

                    total_questions += 1

                total_sets += 1

                if i % 5 == 0:
                    print(f"  Created {i}/{sets_per_subject} sets for {subject_name}")
                    conn.commit()

            conn.commit()
            print(f"Completed {subject_name}: {sets_per_subject} question sets")

        # Print summary
        print(f"\n{'='*60}")
        print(f"SEEDING SUMMARY")
        print(f"{'='*60}")
        print(f"Total Question Sets: {total_sets}")
        print(f"Total Questions: {total_questions}")
        print(f"Average Questions per Set: {total_questions // total_sets}")
        print(f"{'='*60}")

        # Print question type distribution
        cursor.execute("""
            SELECT question_type, COUNT(*) as count
            FROM questions
            GROUP BY question_type
            ORDER BY count DESC
        """)
        print("\nQuestion Type Distribution:")
        for row in cursor.fetchall():
            print(f"  {row['question_type']}: {row['count']}")

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
    print("Y6 PRACTICE EXAM - COMPREHENSIVE DATABASE SEEDER")
    print("Cambridge Year 6 Level - All Subjects")
    print("="*60)

    print("\n1. Clearing all existing questions...")
    clear_all_questions()

    print("\n2. Creating/verifying admin user...")
    seed_admin_user()

    print("\n3. Creating/verifying student user (Rifah)...")
    seed_student_user()

    print("\n4. Seeding question sets (10 per subject, 40 total)...")
    seed_question_sets(10)

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
