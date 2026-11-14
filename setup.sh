#!/bin/bash

################################################################################
#
# Netflix MITM PoC - Transparent Proxy Setup Script
#
# Complete one-command setup for transparent DNS hijacking + HTTPS redirection
#
# Usage:
#   ./setup.sh
#
# This script:
#   1. Checks all dependencies (apktool/jadx, dnsmasq, iptables)
#   2. Extracts domains from Netflix APK files
#   3. Merges extracted domains with known Netflix domain list
#   4. Generates dnsmasq configuration
#   5. Applies iptables rules for traffic redirection
#   6. Verifies the entire setup
#   7. Generates cleanup script for reverting changes
#
# After this script completes, run: docker compose up -d
#
################################################################################

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Counters
SETUP_STEPS=0
SETUP_COMPLETE=0

print_header() {
    echo -e "${BLUE}"
    echo "╔════════════════════════════════════════════════════════════════╗"
    echo "║  Netflix MITM PoC - Transparent Proxy Setup                   ║"
    echo "║  DNS Hijacking + iptables Traffic Redirection                 ║"
    echo "╚════════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

print_step() {
    ((SETUP_STEPS++))
    echo -e "${BLUE}[Step $SETUP_STEPS] $1${NC}"
}

print_success() {
    echo -e "${GREEN}[+] $1${NC}"
    ((SETUP_COMPLETE++))
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
    echo "Setup failed. Please review the errors above."
    exit 1
}

# Function to check if command exists
command_exists() {
    command -v "$1" &> /dev/null
}

# Function to install package
install_package() {
    local package=$1
    print_info "Installing $package..."
    sudo apt-get update > /dev/null
    sudo apt-get install -y "$package" > /dev/null
    print_success "$package installed"
}

print_header

# Step 1: Check dependencies
print_step "Checking dependencies"

# Check for apktool (JAR or command) or jadx
if [ -f scripts/apktool_3.0.2.jar ]; then
    print_success "apktool JAR found (scripts/apktool_3.0.2.jar)"
elif command_exists apktool; then
    print_success "apktool found"
elif command_exists jadx; then
    print_success "jadx found"
else
    print_warning "Neither apktool nor jadx found"
    read -p "Install apktool? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        install_package "apktool"
    else
        print_warning "APK extraction will be skipped, using known domain list only"
    fi
fi

# Check for dnsmasq
if ! command_exists dnsmasq; then
    print_warning "dnsmasq not found"
    read -p "Install dnsmasq? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        install_package "dnsmasq"
    else
        exit_error "dnsmasq is required for DNS hijacking"
    fi
else
    print_success "dnsmasq found"
fi

# Check for iptables
if ! command_exists iptables; then
    exit_error "iptables not found and cannot be installed separately (usually pre-installed)"
else
    print_success "iptables found"
fi

# Check for dig (dnsutils)
if ! command_exists dig; then
    print_warning "dig not found (optional, for verification)"
fi

# Step 2: Prepare directories
print_step "Preparing directories"

mkdir -p domains configs scripts
print_success "Directories created"

# Step 3: Create pre-defined domain list
print_step "Setting up pre-defined Netflix domain list"

if [ ! -f domains/netflix_known.txt ]; then
    cat > domains/netflix_known.txt << 'EOF'
netflix.com
www.netflix.com
nflx.co
api.netflix.com
api-global.netflix.com
signin.netflix.com
secure.netflix.com
graphql.netflix.com
appserver.netflix.com
flixhistory-service.netflix.com
api1.netflix.com
api2.netflix.com
api3.netflix.com
uibootstrap.netflix.com
www-static.netflix.com
cdn-nflx.netflix.com
nflx-ui-prod.netflix.com
apiproxy.netflix.com
msl.netflix.com
membership.netflix.com
payment.netflix.com
promos.netflix.com
secure.nflx.co
www.nflx.co
EOF
    print_success "Created domains/netflix_known.txt"
else
    print_success "domains/netflix_known.txt already exists"
fi

# Step 4: Extract domains from APK (if possible)
print_step "Extracting domains from Netflix APK files"

APK_FILES=$(find ~/Documents/projects/OBLIVION_EDGE_LLC/vetting/NETFLIX_BUGBOUNTY/apk -name "*.apk" 2>/dev/null | head -3)

if [ -z "$APK_FILES" ]; then
    print_warning "No APK files found in expected location"
    print_info "Using known domain list only"
else
    if [ ! -f scripts/extract_domains.py ]; then
        exit_error "scripts/extract_domains.py not found"
    fi

    if python3 scripts/extract_domains.py $APK_FILES 2>&1 | tail -5; then
        print_success "Domain extraction completed"
    else
        print_warning "Domain extraction failed, using known list only"
    fi
fi

# Step 5: Merge domain lists
print_step "Merging domain lists"

# Start with known domains
cat domains/netflix_known.txt > domains/netflix_all.txt

# Add extracted domains if they exist
if [ -f domains/netflix_extracted.txt ]; then
    cat domains/netflix_extracted.txt >> domains/netflix_all.txt
fi

# Remove duplicates and sort
sort -u domains/netflix_all.txt -o domains/netflix_all.txt

TOTAL_DOMAINS=$(wc -l < domains/netflix_all.txt)
print_success "Merged domain list: $TOTAL_DOMAINS unique domains"

# Step 6: Generate dnsmasq configuration
print_step "Generating dnsmasq configuration"

if [ ! -f scripts/generate_dnsmasq_config.py ]; then
    exit_error "scripts/generate_dnsmasq_config.py not found"
fi

python3 scripts/generate_dnsmasq_config.py domains/netflix_all.txt
print_success "Generated configs/dnsmasq.netflix.conf"

# Step 7: Install dnsmasq configuration
print_step "Installing dnsmasq configuration"

print_info "This requires sudo access"
if sudo cp configs/dnsmasq.netflix.conf /etc/dnsmasq.d/netflix-interceptor.conf; then
    print_success "Configuration installed to /etc/dnsmasq.d/netflix-interceptor.conf"

    # Restart dnsmasq
    if sudo systemctl restart dnsmasq; then
        print_success "dnsmasq restarted successfully"
    else
        print_warning "Failed to restart dnsmasq (may need manual restart)"
    fi
else
    exit_error "Failed to install dnsmasq configuration"
fi

# Step 8: Setup iptables rules
print_step "Setting up iptables rules for traffic redirection"

if [ ! -f scripts/setup_iptables.sh ]; then
    exit_error "scripts/setup_iptables.sh not found"
fi

if sudo bash scripts/setup_iptables.sh; then
    print_success "iptables rules configured"
else
    exit_error "Failed to setup iptables rules"
fi

# Step 9: Verify setup
print_step "Verifying transparent proxy setup"

if bash scripts/verify_setup.sh; then
    print_success "Setup verification passed"
else
    print_warning "Some verification tests failed (review output above)"
fi

# Step 10: Create cleanup script
print_step "Creating cleanup script"

cat > cleanup.sh << 'CLEANUP_EOF'
#!/bin/bash
# Generated cleanup script - reverts all system changes
# Usage: sudo ./cleanup.sh

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

if [ -f scripts/cleanup_system.sh ]; then
    sudo bash scripts/cleanup_system.sh
else
    echo "[-] scripts/cleanup_system.sh not found"
    exit 1
fi
CLEANUP_EOF
chmod +x cleanup.sh
print_success "Created cleanup.sh"

# Final summary
echo ""
echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  SETUP COMPLETE!${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
echo ""
echo "Completed steps: $SETUP_COMPLETE / $SETUP_STEPS"
echo ""
echo "Configuration Summary:"
echo "  Total Netflix domains: $TOTAL_DOMAINS"
echo "  dnsmasq config: /etc/dnsmasq.d/netflix-interceptor.conf"
echo "  iptables rules: NETFLIX_INTERCEPT chain (TCP 443→8080)"
echo "  IP forwarding: enabled"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo "  1. Start Docker services:"
echo "     docker compose up -d"
echo ""
echo "  2. Verify traffic is intercepted:"
echo "     docker logs -f netflix_mitm_proxy"
echo ""
echo "  3. Test with Android Netflix app"
echo ""
echo "  4. To revert all changes:"
echo "     sudo ./cleanup.sh"
echo ""
echo -e "${GREEN}Transparent MITM proxy is ready!${NC}"
echo ""
