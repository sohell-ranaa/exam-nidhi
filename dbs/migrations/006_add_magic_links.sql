-- ============================================================================
-- Migration: Add magic_links table for email authentication links
-- ============================================================================

USE y6_practice_exam;

-- Magic Links for passwordless exam access
CREATE TABLE IF NOT EXISTS magic_links (
    id INT AUTO_INCREMENT PRIMARY KEY,
    token VARCHAR(255) NOT NULL UNIQUE,
    user_id INT NOT NULL,
    exam_id INT NULL,
    purpose ENUM('exam_attempt', 'password_reset', 'email_verification') NOT NULL DEFAULT 'exam_attempt',
    expires_at TIMESTAMP NOT NULL,
    used_at TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    KEY idx_token (token),
    KEY idx_user_id (user_id),
    KEY idx_exam_id (exam_id),
    KEY idx_expires (expires_at),

    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (exam_id) REFERENCES practice_exams(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Magic links for passwordless authentication';

-- Insert default SMTP settings if not exists (system_settings table already exists)
INSERT INTO system_settings (setting_key, setting_value) VALUES
('smtp_config', JSON_OBJECT(
    'host', '',
    'port', 587,
    'username', '',
    'password', '',
    'from_email', '',
    'from_name', 'Y6 Practice Exam',
    'use_tls', true
))
ON DUPLICATE KEY UPDATE updated_at = NOW();
