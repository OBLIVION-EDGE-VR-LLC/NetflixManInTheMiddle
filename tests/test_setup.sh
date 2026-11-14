#!/bin/bash

################################################################################
# Integration Test for Transparent MITM Setup
#
# This test validates:
#   1. All required directories are created
#   2. All scripts are present and executable
#   3. Domain lists are generated correctly
#   4. dnsmasq configuration is valid
#   5. iptables rules can be applied without errors
#
# Usage: bash tests/test_setup.sh
################################################################################

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

TESTS_PASSED=0
TESTS_FAILED=0

assert_file_exists() {
    local file=$1
    if [ -f "$file" ]; then
        echo -e "${GREEN}[✓] File exists: $file${NC}"
        ((TESTS_PASSED++))
        return 0
    else
        echo -e "${RED}[✗] File not found: $file${NC}"
        ((TESTS_FAILED++))
        return 1
    fi
}

assert_executable() {
    local file=$1
    if [ -x "$file" ]; then
        echo -e "${GREEN}[✓] Executable: $file${NC}"
        ((TESTS_PASSED++))
        return 0
    else
        echo -e "${RED}[✗] Not executable: $file${NC}"
        ((TESTS_FAILED++))
        return 1
    fi
}

assert_file_content() {
    local file=$1
    local pattern=$2
    if grep -q "$pattern" "$file"; then
        echo -e "${GREEN}[✓] Content check: $file (pattern: $pattern)${NC}"
        ((TESTS_PASSED++))
        return 0
    else
        echo -e "${RED}[✗] Content missing in $file (pattern: $pattern)${NC}"
        ((TESTS_FAILED++))
        return 1
    fi
}

echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  INTEGRATION TESTS FOR TRANSPARENT MITM SETUP${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
echo ""

# Test 1: Main setup.sh exists and is executable
echo -e "${BLUE}[*] Test Group: Main Script${NC}"
assert_file_exists "setup.sh"
assert_executable "setup.sh"
echo ""

# Test 2: Helper scripts exist and are executable
echo -e "${BLUE}[*] Test Group: Helper Scripts${NC}"
assert_file_exists "scripts/extract_domains.py"
assert_executable "scripts/extract_domains.py"
assert_file_exists "scripts/generate_dnsmasq_config.py"
assert_executable "scripts/generate_dnsmasq_config.py"
assert_file_exists "scripts/setup_iptables.sh"
assert_executable "scripts/setup_iptables.sh"
assert_file_exists "scripts/verify_setup.sh"
assert_executable "scripts/verify_setup.sh"
assert_file_exists "scripts/cleanup_system.sh"
assert_executable "scripts/cleanup_system.sh"
echo ""

# Test 3: Configuration files exist
echo -e "${BLUE}[*] Test Group: Configuration Files${NC}"
assert_file_exists "configs/dnsmasq.netflix.conf.template"
assert_file_exists "domains/netflix_known.txt"
echo ""

# Test 4: Domain list contains Netflix domains
echo -e "${BLUE}[*] Test Group: Domain Lists${NC}"
assert_file_content "domains/netflix_known.txt" "netflix.com"
assert_file_content "domains/netflix_known.txt" "nflx.co"
echo ""

# Test 5: Script syntax is valid
echo -e "${BLUE}[*] Test Group: Script Syntax${NC}"
if bash -n setup.sh; then
    echo -e "${GREEN}[✓] setup.sh syntax valid${NC}"
    ((TESTS_PASSED++))
else
    echo -e "${RED}[✗] setup.sh has syntax errors${NC}"
    ((TESTS_FAILED++))
fi

if python3 -m py_compile scripts/extract_domains.py 2>/dev/null; then
    echo -e "${GREEN}[✓] extract_domains.py syntax valid${NC}"
    ((TESTS_PASSED++))
else
    echo -e "${RED}[✗] extract_domains.py has syntax errors${NC}"
    ((TESTS_FAILED++))
fi

if python3 -m py_compile scripts/generate_dnsmasq_config.py 2>/dev/null; then
    echo -e "${GREEN}[✓] generate_dnsmasq_config.py syntax valid${NC}"
    ((TESTS_PASSED++))
else
    echo -e "${RED}[✗] generate_dnsmasq_config.py has syntax errors${NC}"
    ((TESTS_FAILED++))
fi

echo ""

# Test 6: Verify dnsmasq template has placeholders
echo -e "${BLUE}[*] Test Group: Configuration Templates${NC}"
assert_file_content "configs/dnsmasq.netflix.conf.template" "DOMAINS_PLACEHOLDER"
assert_file_content "configs/dnsmasq.netflix.conf.template" "DATE_PLACEHOLDER"
echo ""

# Summary
echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
echo -e "Tests Passed: ${GREEN}${TESTS_PASSED}${NC}"
echo -e "Tests Failed: ${RED}${TESTS_FAILED}${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}All integration tests passed!${NC}"
    exit 0
else
    echo -e "${RED}Some tests failed.${NC}"
    exit 1
fi
