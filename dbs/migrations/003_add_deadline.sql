-- Migration 003: Add deadline column to practice_exams
-- Y6 Practice Exam System

USE y6_practice_exam;

-- Add deadline column to practice_exams
ALTER TABLE practice_exams
    ADD COLUMN IF NOT EXISTS deadline TIMESTAMP NULL AFTER exam_date;

-- Create index for deadline lookups
CREATE INDEX IF NOT EXISTS idx_practice_exams_deadline ON practice_exams(deadline);
