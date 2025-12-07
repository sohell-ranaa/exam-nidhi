-- Migration 002: Add sharing and profile columns
-- Y6 Practice Exam System

USE y6_practice_exam;

-- Add sharing columns to practice_exams
ALTER TABLE practice_exams
    ADD COLUMN IF NOT EXISTS is_public BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS share_token VARCHAR(32) NULL UNIQUE,
    ADD COLUMN IF NOT EXISTS shared_at TIMESTAMP NULL,
    ADD COLUMN IF NOT EXISTS shared_by INT NULL,
    ADD COLUMN IF NOT EXISTS share_views INT DEFAULT 0;

-- Add sharing columns to question_sets
ALTER TABLE question_sets
    ADD COLUMN IF NOT EXISTS is_public BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS share_token VARCHAR(32) NULL UNIQUE,
    ADD COLUMN IF NOT EXISTS shared_at TIMESTAMP NULL,
    ADD COLUMN IF NOT EXISTS share_views INT DEFAULT 0;

-- Add profile columns to users
ALTER TABLE users
    ADD COLUMN IF NOT EXISTS password_changed_at TIMESTAMP NULL,
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP NULL ON UPDATE CURRENT_TIMESTAMP;

-- Create indexes for public sharing
CREATE INDEX IF NOT EXISTS idx_practice_exams_share ON practice_exams(share_token) WHERE is_public = TRUE;
CREATE INDEX IF NOT EXISTS idx_question_sets_share ON question_sets(share_token) WHERE is_public = TRUE;
