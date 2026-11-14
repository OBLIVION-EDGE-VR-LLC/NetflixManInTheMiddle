#!/bin/bash

################################################################################
# iptables Transparent Proxy Setup for MITM Interception
#
# This script:
#   1. Enables IP forwarding (required for traffic redirection)
#   2. Creates iptables rules to redirect HTTPS traffic to MITM proxy
#   3. Saves rules for persistence across reboots
#
# Usage: sudo scripts/setup_iptables.sh
################################################################################

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_header() {
    echo -e "${BLUE}[*] iptables Setup for Netflix Interception${NC}"
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

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    print_error "This script must be run with sudo"
    exit 1
fi

print_header

# Step 1: Enable IP forwarding
print_info "Enabling IP forwarding..."
sysctl -w net.ipv4.ip_forward=1 > /dev/null
print_success "IP forwarding enabled"

# Step 2: Create or clear NETFLIX_INTERCEPT chain
print_info "Setting up iptables chain for Netflix interception..."

# Check if chain exists, delete it if it does
iptables -t nat -L NETFLIX_INTERCEPT -n > /dev/null 2>&1
if [ $? -eq 0 ]; then
    print_info "Clearing existing NETFLIX_INTERCEPT chain..."
    iptables -t nat -F NETFLIX_INTERCEPT
else
    print_info "Creating new NETFLIX_INTERCEPT chain..."
    iptables -t nat -N NETFLIX_INTERCEPT
fi

# Step 3: Add redirection rules
print_info "Adding redirection rules..."

# Redirect HTTPS traffic (port 443) to MITM proxy (port 8080)
# This catches all HTTPS traffic destined for netflix.com (after DNS hijack)
# IMPORTANT: Exclude root user (running mitmproxy) to avoid redirection loop
iptables -t nat -A NETFLIX_INTERCEPT -p tcp --dport 443 -m owner ! --uid-owner root -j REDIRECT --to-port 8080
iptables -t nat -A NETFLIX_INTERCEPT -p tcp --dport 443 -m owner --uid-owner root -j ACCEPT
print_success "Rule added: TCP 443 → 8080 (excluding root traffic)"

# Step 4: Apply chain to PREROUTING (for inbound traffic from Android)
# First, check if NETFLIX_INTERCEPT is already in PREROUTING
iptables -t nat -L PREROUTING -n | grep -q "NETFLIX_INTERCEPT"
if [ $? -ne 0 ]; then
    print_info "Adding NETFLIX_INTERCEPT chain to PREROUTING..."
    iptables -t nat -A PREROUTING -j NETFLIX_INTERCEPT
    print_success "Chain added to PREROUTING"
else
    print_info "NETFLIX_INTERCEPT already in PREROUTING"
fi

# Step 5: Display current rules
print_info "Current iptables NAT rules:"
echo ""
iptables -t nat -L -n | grep -A 20 "NETFLIX_INTERCEPT\|PREROUTING"
echo ""

# Step 6: Save rules to file for reference
print_info "Saving iptables rules to configs/iptables.rules..."
mkdir -p configs
iptables -t nat -L -n > configs/iptables.rules
iptables-save >> configs/iptables.rules 2>/dev/null || true
print_success "Rules saved to configs/iptables.rules"

# Step 7: Persist rules (using iptables-persistent if available)
print_info "Attempting to persist rules..."
if command -v iptables-persistent &> /dev/null; then
    print_info "iptables-persistent found, saving rules..."
    iptables-save | tee /etc/iptables/rules.v4 > /dev/null
    print_success "Rules persisted via iptables-persistent"
elif [ -d /etc/iptables ]; then
    print_info "Saving to /etc/iptables/rules.v4..."
    mkdir -p /etc/iptables
    iptables-save > /etc/iptables/rules.v4
    print_success "Rules saved to /etc/iptables/rules.v4"
else
    echo -e "${YELLOW}[!] iptables-persistent not found - rules may not persist on reboot${NC}"
    print_info "Install with: sudo apt-get install iptables-persistent"
fi

print_info "iptables setup complete!"
print_success "Netflix HTTPS traffic will now redirect to MITM proxy (port 8080)"
