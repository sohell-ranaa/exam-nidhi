"""
Y6 Practice Exam System
Spring Gate Private School, Selangor, Malaysia
Main Flask Application
"""

import sys
from pathlib import Path
from flask import Flask, redirect, url_for, render_template, request

# Add project paths
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src" / "core"))
sys.path.insert(0, str(PROJECT_ROOT / "dbs"))

from config import SECRET_KEY, DEBUG, APP_NAME, SCHOOL_NAME

# Create Flask app
app = Flask(__name__)
app.secret_key = SECRET_KEY
app.config['DEBUG'] = DEBUG

# Register blueprints
from routes.auth import auth_bp
from routes.admin import admin_bp
from routes.student import student_bp
from routes.public import public_bp
from routes.profile import profile_bp
from routes.analytics import analytics_bp
from routes.settings import settings_bp
from routes.questions import questions_bp

app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(student_bp)
app.register_blueprint(public_bp)
app.register_blueprint(profile_bp)
app.register_blueprint(analytics_bp)
app.register_blueprint(settings_bp)
app.register_blueprint(questions_bp)


# Context processor for templates
@app.context_processor
def inject_globals():
    return {
        'app_name': APP_NAME,
        'school_name': SCHOOL_NAME
    }


# Root route
@app.route('/')
def index():
    """Redirect to login or dashboard"""
    from src.core.auth import SessionManager

    session_token = request.cookies.get('session_token')
    if session_token:
        session_data = SessionManager.validate_session(session_token)
        if session_data:
            if session_data['role_name'] == 'Admin':
                return redirect(url_for('admin.dashboard'))
            return redirect(url_for('student.dashboard'))

    return redirect(url_for('auth.login_page'))


# FAQ Page
@app.route('/faq')
def faq():
    """Public FAQ and help page"""
    return render_template('faq.html')


# Error handlers
@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404


@app.errorhandler(403)
def forbidden(e):
    return render_template('403.html'), 403


@app.errorhandler(500)
def server_error(e):
    return render_template('500.html'), 500


if __name__ == '__main__':
    print(f"\n{'='*60}")
    print(f"  {APP_NAME}")
    print(f"  {SCHOOL_NAME}")
    print(f"{'='*60}\n")

    app.run(host='0.0.0.0', port=5001, debug=DEBUG)
