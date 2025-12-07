-- Migration 004: Add scheduled_at timestamp for exam scheduling with time
-- This allows admins to schedule exams at specific times, not just dates

-- Add scheduled_at column to practice_exams
ALTER TABLE practice_exams
ADD COLUMN scheduled_at TIMESTAMP NULL AFTER exam_date;

-- Add index for scheduled_at
ALTER TABLE practice_exams
ADD INDEX idx_practice_exams_scheduled_at (scheduled_at);

-- Update existing records to have scheduled_at based on exam_date at 00:00:00
UPDATE practice_exams
SET scheduled_at = TIMESTAMP(exam_date, '00:00:00')
WHERE scheduled_at IS NULL;
