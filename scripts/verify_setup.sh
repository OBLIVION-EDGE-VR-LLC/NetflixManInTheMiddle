#!/bin/bash

################################################################################
# Verification Script for Transparent MITM Setup
#
# This script verifies:
#   1. dnsmasq is running and resolving Netflix domains to 127.0.0.1
#   2. iptables rules are in place for traffic redirection
#   3. MITM proxy is listening on port 8080
#
# Usage: scripts/verify_setup.sh
################################################################################

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

TESTS_PASSED=0
TESTS_FAILED=0

print_header() {
    echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  TRANSPARENT MITM SETUP VERIFICATION${NC}"
    echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
    echo ""
}

print_test() {
    echo -e "${BLUE}[*] $1${NC}"
}

print_pass() {
    echo -e "${GREEN}[✓] $1${NC}"
    ((TESTS_PASSED++))
}

print_fail() {
    echo -e "${RED}[✗] $1${NC}"
    ((TESTS_FAILED++))
}

print_warning() {
    echo -e "${YELLOW}[!] $1${NC}"
}

print_footer() {
    echo ""
    echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
    echo -e "Tests Passed: ${GREEN}${TESTS_PASSED}${NC}"
    echo -e "Tests Failed: ${RED}${TESTS_FAILED}${NC}"
    echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
}

print_header

# Test 1: Check if dnsmasq is installed
print_test "Checking if dnsmasq is installed..."
if command -v dnsmasq &> /dev/null; then
    print_pass "dnsmasq is installed"
else
    print_fail "dnsmasq not found (install: sudo apt-get install dnsmasq)"
fi

# Test 2: Check if dnsmasq is running
print_test "Checking if dnsmasq is running..."
if pgrep -x dnsmasq > /dev/null; then
    print_pass "dnsmasq is running"
else
    print_warning "dnsmasq is not running (may need to start: sudo systemctl start dnsmasq)"
fi

# Test 3: Check if dnsmasq config exists
print_test "Checking if dnsmasq Netflix config exists..."
if [ -f /etc/dnsmasq.d/netflix-interceptor.conf ]; then
    print_pass "dnsmasq config exists at /etc/dnsmasq.d/netflix-interceptor.conf"
    DOMAIN_COUNT=$(grep -c "^address=" /etc/dnsmasq.d/netflix-interceptor.conf 2>/dev/null || echo 0)
    print_pass "Config contains $DOMAIN_COUNT domain redirects"
else
    print_fail "dnsmasq config not found at /etc/dnsmasq.d/netflix-interceptor.conf"
fi

# Test 4: Test DNS resolution (if dnsmasq running)
print_test "Testing DNS resolution of netflix.com..."
if pgrep -x dnsmasq > /dev/null; then
    RESOLVED_IP=$(dig +short netflix.com @127.0.0.1 2>/dev/null | head -1)
    if [ "$RESOLVED_IP" = "127.0.0.1" ]; then
        print_pass "netflix.com resolves to 127.0.0.1"
    else
        print_warning "netflix.com resolved to $RESOLVED_IP (expected 127.0.0.1)"
    fi
else
    print_warning "Skipping DNS test (dnsmasq not running)"
fi

# Test 5: Check iptables rules
print_test "Checking iptables NETFLIX_INTERCEPT chain..."
if sudo iptables -t nat -L NETFLIX_INTERCEPT -n &> /dev/null; then
    print_pass "NETFLIX_INTERCEPT chain exists"

    # Check for redirect rule
    if sudo iptables -t nat -L NETFLIX_INTERCEPT -n | grep -q "REDIRECT.*tcp.*443.*8080"; then
        print_pass "HTTPS redirect rule (443→8080) is installed"
    else
        print_fail "HTTPS redirect rule not found"
    fi
else
    print_fail "NETFLIX_INTERCEPT chain not found"
fi

# Test 6: Check if MITM proxy is listening
print_test "Checking if MITM proxy is listening on port 8080..."
if netstat -tuln 2>/dev/null | grep -q ":8080 " || ss -tuln 2>/dev/null | grep -q ":8080 "; then
    print_pass "MITM proxy is listening on port 8080"
else
    print_warning "Port 8080 is not listening (Docker service may not be running yet)"
fi

# Test 7: Check Docker services
print_test "Checking Docker services..."
if command -v docker &> /dev/null; then
    if docker ps | grep -q netflix_mitm_proxy; then
        print_pass "MITM proxy Docker container is running"
    else
        print_warning "MITM proxy container not running (run: docker compose up -d)"
    fi
else
    print_warning "Docker not found (needed for MITM proxy)"
fi

# Test 8: Check IP forwarding
print_test "Checking IP forwarding..."
IP_FORWARD=$(cat /proc/sys/net/ipv4/ip_forward 2>/dev/null)
if [ "$IP_FORWARD" = "1" ]; then
    print_pass "IP forwarding is enabled"
else
    print_warning "IP forwarding is disabled (should be enabled for redirection)"
fi

# Print summary
print_footer

# Exit with appropriate code
if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}All critical tests passed! Setup is ready.${NC}"
    exit 0
else
    echo -e "${YELLOW}Some tests failed. Review the output above.${NC}"
    exit 1
fi
