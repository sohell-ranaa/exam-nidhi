-- ============================================================================
-- Migration 002: Add Drawing Question Support
-- Y6 Practice Exam System
-- ============================================================================

USE y6_practice_exam;

-- Add 'drawing' to question_type ENUM
ALTER TABLE questions
MODIFY COLUMN question_type ENUM('mcq', 'written', 'fill_blank', 'matching', 'labeling', 'drawing') NOT NULL;

-- Add drawing_template field for predefined shapes/backgrounds
ALTER TABLE questions
ADD COLUMN drawing_template JSON NULL COMMENT 'Template config: {"type": "flowchart|freehand|connect", "background_url": "...", "predefined_shapes": [...]}'
AFTER labels;

-- Add drawing_data field to student_answers for storing base64 canvas data
ALTER TABLE student_answers
ADD COLUMN drawing_data LONGTEXT NULL COMMENT 'Base64 encoded canvas image data'
AFTER student_answer;

-- ============================================================================
-- MIGRATION COMPLETE
-- ============================================================================
