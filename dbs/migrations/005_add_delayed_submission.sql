-- Migration 005: Add is_delayed column for late submissions
-- Submissions after 60 minutes from started_at are marked as delayed

-- Add is_delayed column to practice_exams
ALTER TABLE practice_exams
ADD COLUMN is_delayed BOOLEAN DEFAULT FALSE AFTER submitted_at;

-- Add index for filtering delayed exams
ALTER TABLE practice_exams
ADD INDEX idx_practice_exams_is_delayed (is_delayed);
