#!/bin/bash
# Test script for suffix parsing functionality
# Tests the parse_package_suffix and validate_suffix functions

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counters
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

# Source the suffix parsing functions from the workflow
# (These functions will be extracted to a separate file for testing)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/suffix-parsing-functions.sh"

# Test helper functions
test_case() {
  local name="$1"
  echo -e "\n${YELLOW}Test: $name${NC}"
  TESTS_RUN=$((TESTS_RUN + 1))
}

assert_equals() {
  local expected="$1"
  local actual="$2"
  local message="$3"

  if [ "$expected" = "$actual" ]; then
    echo -e "${GREEN}✓ PASS${NC}: $message"
    TESTS_PASSED=$((TESTS_PASSED + 1))
    return 0
  else
    echo -e "${RED}✗ FAIL${NC}: $message"
    echo "  Expected: $expected"
    echo "  Actual:   $actual"
    TESTS_FAILED=$((TESTS_FAILED + 1))
    return 1
  fi
}

print_summary() {
  echo -e "\n========================================="
  echo "Test Summary"
  echo "========================================="
  echo "Tests run:    $TESTS_RUN"
  echo -e "${GREEN}Tests passed: $TESTS_PASSED${NC}"
  if [ $TESTS_FAILED -gt 0 ]; then
    echo -e "${RED}Tests failed: $TESTS_FAILED${NC}"
  else
    echo -e "${GREEN}Tests failed: $TESTS_FAILED${NC}"
  fi
  echo "========================================="

  if [ $TESTS_FAILED -gt 0 ]; then
    exit 1
  fi
}

# Test 1: Parse valid suffix with any+hatlabs
test_case "Parse valid suffix: any+hatlabs"
parse_package_suffix "halpi2-daemon_1.0.0-1_all+any+hatlabs.deb" distro component
assert_equals "any" "$distro" "Distro should be 'any'"
assert_equals "hatlabs" "$component" "Component should be 'hatlabs'"

# Test 2: Parse valid suffix with trixie+main
test_case "Parse valid suffix: trixie+main"
parse_package_suffix "signalk_2.17.2-1_all+trixie+main.deb" distro component
assert_equals "trixie" "$distro" "Distro should be 'trixie'"
assert_equals "main" "$component" "Component should be 'main'"

# Test 3: Parse valid suffix with bookworm+main
test_case "Parse valid suffix: bookworm+main"
parse_package_suffix "package_1.0-1_all+bookworm+main.deb" distro component
assert_equals "bookworm" "$distro" "Distro should be 'bookworm'"
assert_equals "main" "$component" "Component should be 'main'"

# Test 4: No suffix - fallback to defaults
test_case "No suffix - fallback to defaults"
parse_package_suffix "old-package_1.0-1_all.deb" distro component
assert_equals "any" "$distro" "Distro should fallback to 'any'"
assert_equals "main" "$component" "Component should fallback to 'main'"

# Test 5: Invalid distro - should warn and fallback
test_case "Invalid distro - fallback"
parse_package_suffix "package_1.0-1_all+invalid+main.deb" distro component
# Should parse but validation should fail
# For now, just check it extracts the values
assert_equals "invalid" "$distro" "Should extract distro even if invalid"
assert_equals "main" "$component" "Component should be 'main'"

# Test 6: Invalid component - should warn and fallback
test_case "Invalid component - fallback"
parse_package_suffix "package_1.0-1_all+trixie+invalid.deb" distro component
assert_equals "trixie" "$distro" "Distro should be 'trixie'"
assert_equals "invalid" "$component" "Should extract component even if invalid"

# Test 7: Malformed suffix (single +) - fallback
test_case "Malformed suffix (single +) - fallback"
parse_package_suffix "package_1.0-1_all+trixie.deb" distro component
assert_equals "any" "$distro" "Should fallback to 'any'"
assert_equals "main" "$component" "Should fallback to 'main'"

# Test 8: Complex package name with dashes and numbers
test_case "Complex package name"
parse_package_suffix "cockpit-apt-manager_2.1.0-1_all+trixie+main.deb" distro component
assert_equals "trixie" "$distro" "Should parse trixie from complex name"
assert_equals "main" "$component" "Should parse main from complex name"

# Test 9: Package with forky (future distro)
test_case "Future distro: forky+main"
parse_package_suffix "package_1.0-1_all+forky+main.deb" distro component
assert_equals "forky" "$distro" "Distro should be 'forky'"
assert_equals "main" "$component" "Component should be 'main'"

# Test 10: Validate known distros
test_case "Validate known distro: trixie"
if validate_suffix "trixie" "main"; then
  echo -e "${GREEN}✓ PASS${NC}: trixie is valid distro"
  TESTS_PASSED=$((TESTS_PASSED + 1))
else
  echo -e "${RED}✗ FAIL${NC}: trixie should be valid distro"
  TESTS_FAILED=$((TESTS_FAILED + 1))
fi

# Test 11: Validate unknown distro
test_case "Validate unknown distro: invalid"
if ! validate_suffix "invalid" "main"; then
  echo -e "${GREEN}✓ PASS${NC}: invalid distro correctly rejected"
  TESTS_PASSED=$((TESTS_PASSED + 1))
else
  echo -e "${RED}✗ FAIL${NC}: invalid distro should be rejected"
  TESTS_FAILED=$((TESTS_FAILED + 1))
fi

# Test 12: Validate known component
test_case "Validate known component: hatlabs"
if validate_suffix "any" "hatlabs"; then
  echo -e "${GREEN}✓ PASS${NC}: hatlabs is valid component"
  TESTS_PASSED=$((TESTS_PASSED + 1))
else
  echo -e "${RED}✗ FAIL${NC}: hatlabs should be valid component"
  TESTS_FAILED=$((TESTS_FAILED + 1))
fi

# Test 13: Validate unknown component
test_case "Validate unknown component: invalid"
if ! validate_suffix "any" "invalid"; then
  echo -e "${GREEN}✓ PASS${NC}: invalid component correctly rejected"
  TESTS_PASSED=$((TESTS_PASSED + 1))
else
  echo -e "${RED}✗ FAIL${NC}: invalid component should be rejected"
  TESTS_FAILED=$((TESTS_FAILED + 1))
fi

# Print summary
print_summary
