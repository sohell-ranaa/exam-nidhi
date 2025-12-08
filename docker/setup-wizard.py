#!/usr/bin/env python3
"""
Y6 Practice Exam - First-Run Setup Wizard
Interactive configuration for Docker deployment
"""

import os
import sys
import re
import secrets
import getpass

CONFIG_DIR = os.environ.get('CONFIG_DIR', '/app/config')
CONFIG_FILE = os.path.join(CONFIG_DIR, 'app.env')
SETUP_FLAG = os.path.join(CONFIG_DIR, '.setup_complete')

# Colors
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'═' * 60}{Colors.END}")
    print(f"{Colors.HEADER}{Colors.BOLD}  {text}{Colors.END}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'═' * 60}{Colors.END}\n")

def print_section(text):
    print(f"\n{Colors.CYAN}{Colors.BOLD}▶ {text}{Colors.END}")
    print(f"{Colors.CYAN}{'─' * 50}{Colors.END}")

def print_success(text):
    print(f"{Colors.GREEN}✓ {text}{Colors.END}")

def print_warning(text):
    print(f"{Colors.YELLOW}⚠ {text}{Colors.END}")

def print_error(text):
    print(f"{Colors.RED}✗ {text}{Colors.END}")

def prompt(message, default=None, required=True, password=False, validate=None):
    """Get user input with optional default and validation"""
    while True:
        if default:
            display = f"{Colors.BLUE}{message} [{default}]: {Colors.END}"
        else:
            display = f"{Colors.BLUE}{message}: {Colors.END}"

        if password:
            value = getpass.getpass(display)
        else:
            value = input(display).strip()

        if not value and default:
            value = default

        if required and not value:
            print_error("This field is required.")
            continue

        if validate and value:
            is_valid, error = validate(value)
            if not is_valid:
                print_error(error)
                continue

        return value

def prompt_yes_no(message, default=True):
    """Get yes/no input"""
    default_str = "Y/n" if default else "y/N"
    response = input(f"{Colors.BLUE}{message} [{default_str}]: {Colors.END}").strip().lower()

    if not response:
        return default
    return response in ('y', 'yes', 'true', '1')

def validate_port(value):
    """Validate port number"""
    try:
        port = int(value)
        if 1 <= port <= 65535:
            return True, None
        return False, "Port must be between 1 and 65535"
    except ValueError:
        return False, "Port must be a number"

def validate_email(value):
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if re.match(pattern, value):
        return True, None
    return False, "Invalid email format"

def test_database_connection(config):
    """Test database connection"""
    try:
        import mysql.connector
        conn = mysql.connector.connect(
            host=config['DB_HOST'],
            port=int(config['DB_PORT']),
            user=config['DB_USER'],
            password=config['DB_PASSWORD'],
            database=config.get('DB_NAME', ''),
            connect_timeout=10
        )
        conn.close()
        return True, None
    except Exception as e:
        return False, str(e)

def test_smtp_connection(config):
    """Test SMTP connection"""
    if not config.get('SMTP_ENABLED', 'false').lower() == 'true':
        return True, "SMTP disabled"

    try:
        import smtplib
        import ssl

        host = config['SMTP_HOST']
        port = int(config['SMTP_PORT'])
        use_tls = config.get('SMTP_USE_TLS', 'true').lower() == 'true'

        if use_tls:
            context = ssl.create_default_context()
            server = smtplib.SMTP(host, port, timeout=10)
            server.starttls(context=context)
        else:
            server = smtplib.SMTP(host, port, timeout=10)

        server.login(config['SMTP_USER'], config['SMTP_PASSWORD'])
        server.quit()
        return True, None
    except Exception as e:
        return False, str(e)

def run_setup():
    """Run the interactive setup wizard"""
    print_header("Y6 Practice Exam - Setup Wizard")

    print(f"""
{Colors.CYAN}Welcome to the Y6 Practice Exam System setup!{Colors.END}

This wizard will help you configure:
  • Database connection (MySQL/MariaDB)
  • Email settings (SMTP for magic links)
  • Application settings
  • Admin account

{Colors.YELLOW}Note: You can re-run this setup anytime with: docker exec -it <container> setup{Colors.END}
""")

    if not prompt_yes_no("Ready to begin setup?", default=True):
        print_warning("Setup cancelled.")
        sys.exit(1)

    config = {}

    # ─────────────────────────────────────────────────────────
    # Database Configuration
    # ─────────────────────────────────────────────────────────
    print_section("Database Configuration")

    print(f"{Colors.YELLOW}You need a MySQL/MariaDB database. The database should already exist.{Colors.END}\n")

    config['DB_HOST'] = prompt("Database host", default="localhost")
    config['DB_PORT'] = prompt("Database port", default="3306", validate=validate_port)
    config['DB_NAME'] = prompt("Database name", default="y6_practice_exam")
    config['DB_USER'] = prompt("Database username", default="root")
    config['DB_PASSWORD'] = prompt("Database password", password=True)

    # Test database connection
    print(f"\n{Colors.YELLOW}Testing database connection...{Colors.END}")
    success, error = test_database_connection(config)
    if success:
        print_success("Database connection successful!")
    else:
        print_error(f"Database connection failed: {error}")
        if not prompt_yes_no("Continue anyway?", default=False):
            print_warning("Please fix database settings and try again.")
            sys.exit(1)

    # ─────────────────────────────────────────────────────────
    # Email Configuration
    # ─────────────────────────────────────────────────────────
    print_section("Email Configuration (SMTP)")

    print(f"{Colors.YELLOW}Email is used for magic link logins and notifications.{Colors.END}\n")

    if prompt_yes_no("Enable email functionality?", default=True):
        config['SMTP_ENABLED'] = 'true'
        config['SMTP_HOST'] = prompt("SMTP host", default="smtp.gmail.com")
        config['SMTP_PORT'] = prompt("SMTP port", default="587", validate=validate_port)
        config['SMTP_USER'] = prompt("SMTP username/email", validate=validate_email)
        config['SMTP_PASSWORD'] = prompt("SMTP password/app password", password=True)
        config['SMTP_FROM_NAME'] = prompt("From name", default="Y6 Practice Exam")
        config['SMTP_FROM_EMAIL'] = prompt("From email", default=config['SMTP_USER'], validate=validate_email)
        config['SMTP_USE_TLS'] = 'true' if prompt_yes_no("Use TLS?", default=True) else 'false'

        # Test SMTP connection
        print(f"\n{Colors.YELLOW}Testing SMTP connection...{Colors.END}")
        success, error = test_smtp_connection(config)
        if success:
            print_success("SMTP connection successful!")
        else:
            print_error(f"SMTP connection failed: {error}")
            if not prompt_yes_no("Continue anyway?", default=True):
                config['SMTP_ENABLED'] = 'false'
    else:
        config['SMTP_ENABLED'] = 'false'
        print_warning("Email disabled. Users will need to login with password.")

    # ─────────────────────────────────────────────────────────
    # Application Settings
    # ─────────────────────────────────────────────────────────
    print_section("Application Settings")

    config['SECRET_KEY'] = secrets.token_hex(32)
    config['APP_ENV'] = 'production'
    config['DEBUG'] = 'false'

    config['SCHOOL_NAME'] = prompt("School name", default="Spring Gate Private School")
    config['APP_NAME'] = prompt("Application name", default="Y6 Practice Exam")

    # ─────────────────────────────────────────────────────────
    # Admin Account
    # ─────────────────────────────────────────────────────────
    print_section("Admin Account")

    print(f"{Colors.YELLOW}Create the main admin account for managing the system.{Colors.END}\n")

    config['ADMIN_NAME'] = prompt("Admin full name", default="Administrator")
    config['ADMIN_EMAIL'] = prompt("Admin email", validate=validate_email)
    config['ADMIN_PASSWORD'] = prompt("Admin password (min 8 chars)", password=True,
                                      validate=lambda x: (len(x) >= 8, "Password must be at least 8 characters"))

    # ─────────────────────────────────────────────────────────
    # Student Account
    # ─────────────────────────────────────────────────────────
    print_section("Student Account")

    if prompt_yes_no("Create a student account now?", default=True):
        config['STUDENT_NAME'] = prompt("Student full name", default="Student")
        config['STUDENT_EMAIL'] = prompt("Student email", validate=validate_email)
        config['CREATE_STUDENT'] = 'true'
    else:
        config['CREATE_STUDENT'] = 'false'

    # ─────────────────────────────────────────────────────────
    # Auto-Update Settings
    # ─────────────────────────────────────────────────────────
    print_section("Auto-Update Settings")

    if prompt_yes_no("Enable auto-update from GitHub on restart?", default=True):
        config['AUTO_UPDATE'] = 'true'
        config['GITHUB_REPO'] = prompt("GitHub repository URL",
                                       default="https://github.com/yourusername/y6-practice-exam.git")
    else:
        config['AUTO_UPDATE'] = 'false'

    # ─────────────────────────────────────────────────────────
    # Seed Data
    # ─────────────────────────────────────────────────────────
    print_section("Sample Data")

    if prompt_yes_no("Seed sample questions (500+ questions for all subjects)?", default=True):
        config['SEED_DATA'] = 'true'
    else:
        config['SEED_DATA'] = 'false'

    # ─────────────────────────────────────────────────────────
    # Save Configuration
    # ─────────────────────────────────────────────────────────
    print_section("Saving Configuration")

    # Ensure config directory exists
    os.makedirs(CONFIG_DIR, exist_ok=True)

    # Write config file
    with open(CONFIG_FILE, 'w') as f:
        f.write("# Y6 Practice Exam Configuration\n")
        f.write("# Generated by setup wizard\n\n")

        f.write("# Database\n")
        for key in ['DB_HOST', 'DB_PORT', 'DB_NAME', 'DB_USER', 'DB_PASSWORD']:
            f.write(f"{key}={config.get(key, '')}\n")

        f.write("\n# Email (SMTP)\n")
        for key in ['SMTP_ENABLED', 'SMTP_HOST', 'SMTP_PORT', 'SMTP_USER', 'SMTP_PASSWORD',
                    'SMTP_FROM_NAME', 'SMTP_FROM_EMAIL', 'SMTP_USE_TLS']:
            if key in config:
                f.write(f"{key}={config[key]}\n")

        f.write("\n# Application\n")
        for key in ['SECRET_KEY', 'APP_ENV', 'DEBUG', 'SCHOOL_NAME', 'APP_NAME']:
            f.write(f"{key}={config.get(key, '')}\n")

        f.write("\n# Admin Account\n")
        for key in ['ADMIN_NAME', 'ADMIN_EMAIL', 'ADMIN_PASSWORD']:
            f.write(f"{key}={config.get(key, '')}\n")

        f.write("\n# Student Account\n")
        for key in ['CREATE_STUDENT', 'STUDENT_NAME', 'STUDENT_EMAIL']:
            if key in config:
                f.write(f"{key}={config[key]}\n")

        f.write("\n# Updates\n")
        for key in ['AUTO_UPDATE', 'GITHUB_REPO']:
            if key in config:
                f.write(f"{key}={config[key]}\n")

        f.write("\n# Data\n")
        f.write(f"SEED_DATA={config.get('SEED_DATA', 'false')}\n")

    print_success(f"Configuration saved to {CONFIG_FILE}")

    # Create setup complete flag
    with open(SETUP_FLAG, 'w') as f:
        f.write("Setup completed\n")

    print_success("Setup flag created")

    # ─────────────────────────────────────────────────────────
    # Create Admin/Student Accounts
    # ─────────────────────────────────────────────────────────
    print_section("Creating User Accounts")

    try:
        # Load config as environment variables
        for key, value in config.items():
            os.environ[key] = value

        # Import after setting env vars
        sys.path.insert(0, '/app')
        from dbs.connection import get_connection
        from src.core.auth import PasswordManager

        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        # Check if roles exist, create if not
        cursor.execute("SELECT id FROM roles WHERE name = 'Admin'")
        if not cursor.fetchone():
            cursor.execute("INSERT INTO roles (id, name, description) VALUES (1, 'Admin', 'Administrator')")
            cursor.execute("INSERT INTO roles (id, name, description) VALUES (2, 'Student', 'Student')")
            conn.commit()
            print_success("Created roles")

        # Create admin
        cursor.execute("SELECT id FROM users WHERE email = %s", (config['ADMIN_EMAIL'],))
        if not cursor.fetchone():
            password_hash = PasswordManager.hash_password(config['ADMIN_PASSWORD'])
            cursor.execute("""
                INSERT INTO users (full_name, email, password_hash, role_id, is_active, email_verified)
                VALUES (%s, %s, %s, 1, TRUE, TRUE)
            """, (config['ADMIN_NAME'], config['ADMIN_EMAIL'], password_hash))
            conn.commit()
            print_success(f"Created admin account: {config['ADMIN_EMAIL']}")
        else:
            print_warning(f"Admin account already exists: {config['ADMIN_EMAIL']}")

        # Create student if requested
        if config.get('CREATE_STUDENT') == 'true':
            cursor.execute("SELECT id FROM users WHERE email = %s", (config['STUDENT_EMAIL'],))
            if not cursor.fetchone():
                cursor.execute("""
                    INSERT INTO users (full_name, email, role_id, is_active, email_verified)
                    VALUES (%s, %s, 2, TRUE, TRUE)
                """, (config['STUDENT_NAME'], config['STUDENT_EMAIL']))
                conn.commit()
                print_success(f"Created student account: {config['STUDENT_EMAIL']}")
            else:
                print_warning(f"Student account already exists: {config['STUDENT_EMAIL']}")

        cursor.close()
        conn.close()

    except Exception as e:
        print_warning(f"Could not create accounts now: {e}")
        print_warning("Accounts will be created when the app starts.")

    # ─────────────────────────────────────────────────────────
    # Complete
    # ─────────────────────────────────────────────────────────
    print_header("Setup Complete!")

    print(f"""
{Colors.GREEN}Your Y6 Practice Exam system is configured!{Colors.END}

{Colors.CYAN}Access the application at:{Colors.END}
  http://localhost:5001

{Colors.CYAN}Login credentials:{Colors.END}
  Admin: {config['ADMIN_EMAIL']}
  Password: (the password you entered)
""")

    if config.get('CREATE_STUDENT') == 'true':
        print(f"""  Student: {config['STUDENT_EMAIL']}
  (Use magic link or set password in admin panel)
""")

    print(f"""
{Colors.YELLOW}Tips:{Colors.END}
  • Re-run setup: docker exec -it <container> setup
  • View logs: docker logs -f <container>
  • Update app: docker exec -it <container> update

{Colors.GREEN}The application will now start...{Colors.END}
""")

    return 0

if __name__ == '__main__':
    try:
        sys.exit(run_setup())
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Setup cancelled by user.{Colors.END}")
        sys.exit(1)
    except Exception as e:
        print(f"\n{Colors.RED}Setup failed: {e}{Colors.END}")
        sys.exit(1)
