-- ============================================================================
-- Y6 Practice Exam System - Database Schema
-- Spring Gate Private School, Selangor, Malaysia
-- ============================================================================

-- Create database if not exists
CREATE DATABASE IF NOT EXISTS y6_practice_exam
CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE y6_practice_exam;

SET FOREIGN_KEY_CHECKS = 0;

-- ============================================================================
-- AUTHENTICATION & USER MANAGEMENT (adapted from ssh-guardian v3)
-- ============================================================================

-- ----------------------------------------------------------------------------
-- Roles (RBAC)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS roles (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,
    description TEXT NULL,
    permissions JSON NOT NULL COMMENT 'Permission flags',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='RBAC roles with JSON permissions';

-- ----------------------------------------------------------------------------
-- Users
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    role_id INT NOT NULL,

    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    is_email_verified BOOLEAN DEFAULT FALSE,

    -- Security
    last_login TIMESTAMP NULL,
    failed_login_attempts INT DEFAULT 0,
    locked_until TIMESTAMP NULL,

    -- Metadata
    created_by INT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    KEY idx_role_id (role_id),
    KEY idx_is_active (is_active),

    FOREIGN KEY (role_id) REFERENCES roles(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='User accounts with RBAC';

-- ----------------------------------------------------------------------------
-- User Sessions
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS user_sessions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    session_token VARCHAR(255) NOT NULL UNIQUE,
    ip_address VARCHAR(45) NULL,
    user_agent TEXT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    KEY idx_user_id (user_id),
    KEY idx_expires_at (expires_at),

    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Active user sessions';

-- ----------------------------------------------------------------------------
-- User OTPs (One-Time Passwords)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS user_otps (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    otp_code VARCHAR(6) NOT NULL,
    purpose ENUM('login', 'password_reset', 'email_verification') DEFAULT 'login',
    expires_at TIMESTAMP NOT NULL,
    is_used BOOLEAN DEFAULT FALSE,
    used_at TIMESTAMP NULL,
    ip_address VARCHAR(45) NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    KEY idx_user_id (user_id),
    KEY idx_otp_lookup (user_id, otp_code, purpose, is_used),

    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='OTP codes for two-factor authentication';

-- ----------------------------------------------------------------------------
-- Audit Logs
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS audit_logs (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NULL,
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50) NULL,
    resource_id VARCHAR(100) NULL,
    details JSON NULL,
    ip_address VARCHAR(45) NULL,
    user_agent TEXT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    KEY idx_user_id (user_id),
    KEY idx_action (action),
    KEY idx_created_at (created_at),

    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Audit trail for security events';

-- ============================================================================
-- EXAM SYSTEM TABLES
-- ============================================================================

-- ----------------------------------------------------------------------------
-- Subjects
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS subjects (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,
    code VARCHAR(10) NOT NULL UNIQUE,
    description TEXT NULL,
    icon VARCHAR(50) NULL,
    color VARCHAR(7) NULL COMMENT 'Hex color code',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Academic subjects';

-- ----------------------------------------------------------------------------
-- Question Sets (Exam Papers)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS question_sets (
    id INT AUTO_INCREMENT PRIMARY KEY,
    subject_id INT NOT NULL,
    title VARCHAR(200) NOT NULL,
    description TEXT NULL,
    total_marks INT DEFAULT 50,
    duration_minutes INT DEFAULT 60,
    difficulty ENUM('easy', 'medium', 'hard') DEFAULT 'medium',
    is_active BOOLEAN DEFAULT TRUE,
    created_by INT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    KEY idx_subject_id (subject_id),
    KEY idx_is_active (is_active),

    FOREIGN KEY (subject_id) REFERENCES subjects(id),
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Question sets / exam papers';

-- ----------------------------------------------------------------------------
-- Questions
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS questions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    question_set_id INT NOT NULL,
    question_number INT NOT NULL,
    question_type ENUM('mcq', 'written', 'fill_blank', 'matching', 'labeling') NOT NULL,
    question_text TEXT NOT NULL,
    question_html TEXT NULL COMMENT 'Rich text version',
    image_url VARCHAR(500) NULL COMMENT 'For diagram/image questions',
    marks INT DEFAULT 1,

    -- Answer data (JSON format for flexibility)
    correct_answer TEXT NOT NULL COMMENT 'JSON for complex answers',
    options JSON NULL COMMENT 'For MCQ: ["option1", "option2", ...]',
    matching_pairs JSON NULL COMMENT 'For matching: [{"left": "A", "right": "1"}, ...]',
    labels JSON NULL COMMENT 'For labeling: [{"position": "top", "answer": "heart"}, ...]',

    -- Hints and explanations
    hint TEXT NULL,
    explanation TEXT NULL COMMENT 'Shown after answer release',

    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    KEY idx_question_set_id (question_set_id),
    KEY idx_question_number (question_number),
    KEY idx_question_type (question_type),

    FOREIGN KEY (question_set_id) REFERENCES question_sets(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Individual questions';

-- ----------------------------------------------------------------------------
-- Practice Exams (Assigned to students)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS practice_exams (
    id INT AUTO_INCREMENT PRIMARY KEY,
    student_id INT NOT NULL,
    question_set_id INT NOT NULL,
    exam_date DATE NOT NULL,

    -- Status workflow: pending -> in_progress -> submitted -> grading -> released
    status ENUM('pending', 'in_progress', 'submitted', 'grading', 'released') DEFAULT 'pending',

    -- Timestamps
    started_at TIMESTAMP NULL,
    submitted_at TIMESTAMP NULL,
    graded_at TIMESTAMP NULL COMMENT 'When admin finishes grading written answers',
    released_at TIMESTAMP NULL,

    -- Scores
    total_score INT NULL,
    max_score INT NULL,
    auto_graded_score INT NULL COMMENT 'Score from auto-graded questions',
    manual_graded_score INT NULL COMMENT 'Score from manually graded questions',
    percentage DECIMAL(5,2) NULL,

    -- Flags
    answers_released BOOLEAN DEFAULT FALSE,

    -- Admin notes
    admin_notes TEXT NULL,
    graded_by INT NULL,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    KEY idx_student_id (student_id),
    KEY idx_question_set_id (question_set_id),
    KEY idx_exam_date (exam_date),
    KEY idx_status (status),

    FOREIGN KEY (student_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (question_set_id) REFERENCES question_sets(id),
    FOREIGN KEY (graded_by) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Practice exams assigned to students';

-- ----------------------------------------------------------------------------
-- Student Answers
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS student_answers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    practice_exam_id INT NOT NULL,
    question_id INT NOT NULL,

    -- Student's answer (JSON for complex types)
    student_answer TEXT NULL,

    -- Grading
    is_correct BOOLEAN NULL,
    marks_awarded INT NULL,
    auto_graded BOOLEAN DEFAULT FALSE COMMENT 'Was this auto-graded?',

    -- Admin feedback for written answers
    admin_feedback TEXT NULL,

    -- Timestamps
    answered_at TIMESTAMP NULL,
    graded_at TIMESTAMP NULL,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    KEY idx_practice_exam_id (practice_exam_id),
    KEY idx_question_id (question_id),

    UNIQUE KEY uk_exam_question (practice_exam_id, question_id),

    FOREIGN KEY (practice_exam_id) REFERENCES practice_exams(id) ON DELETE CASCADE,
    FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Student answers to questions';

-- ============================================================================
-- INSERT DEFAULT DATA
-- ============================================================================

-- Insert default roles (adapted for exam system)
INSERT INTO roles (id, name, description, permissions) VALUES
(1, 'Admin', 'Full system access - can manage exams and grade answers', JSON_OBJECT(
    'dashboard_access', true,
    'user_management', true,
    'exam_management', true,
    'question_management', true,
    'grade_answers', true,
    'release_answers', true,
    'view_reports', true
)),
(2, 'Student', 'Student access - can take exams and view released results', JSON_OBJECT(
    'dashboard_access', true,
    'take_exams', true,
    'view_results', true
));

-- Insert default subjects
INSERT INTO subjects (id, name, code, description, icon, color) VALUES
(1, 'English', 'ENG', 'English Language - Reading, Writing, Grammar', 'book', '#3498db'),
(2, 'Mathematics', 'MAT', 'Mathematics - Arithmetic, Geometry, Problem Solving', 'calculator', '#e74c3c'),
(3, 'ICT', 'ICT', 'Information and Communication Technology', 'laptop', '#9b59b6'),
(4, 'Science', 'SCI', 'Science - Biology, Physics, Chemistry basics', 'flask', '#2ecc71');

SET FOREIGN_KEY_CHECKS = 1;

-- ============================================================================
-- SCHEMA CREATION COMPLETE
-- ============================================================================
