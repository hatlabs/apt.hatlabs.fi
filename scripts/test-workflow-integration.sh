#!/bin/bash
# Test script for workflow integration
# Simulates the actual GitHub Actions workflow to identify issues

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Test counters
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

# Source the functions
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/suffix-parsing-functions.sh"
source "$SCRIPT_DIR/routing-functions.sh"

# Create temporary test directory
TEST_DIR=$(mktemp -d)
trap "rm -rf $TEST_DIR" EXIT

test_case() {
  local name="$1"
  echo -e "\n${YELLOW}Test: $name${NC}"
  TESTS_RUN=$((TESTS_RUN + 1))
}

assert_file_exists() {
  local filepath="$1"
  local message="$2"

  if [ -f "$filepath" ]; then
    echo -e "${GREEN}✓ PASS${NC}: $message"
    TESTS_PASSED=$((TESTS_PASSED + 1))
    return 0
  else
    echo -e "${RED}✗ FAIL${NC}: $message"
    echo "  Expected file: $filepath"
    TESTS_FAILED=$((TESTS_FAILED + 1))
    return 1
  fi
}

assert_file_not_exists() {
  local filepath="$1"
  local message="$2"

  if [ ! -f "$filepath" ]; then
    echo -e "${GREEN}✓ PASS${NC}: $message"
    TESTS_PASSED=$((TESTS_PASSED + 1))
    return 0
  else
    echo -e "${RED}✗ FAIL${NC}: $message"
    echo "  Unexpected file: $filepath"
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

# Helper function to create test package
create_test_package() {
  local package_name="$1"
  local version="$2"
  local arch="$3"
  local distro="$4"
  local component="$5"

  local canonical_name="${package_name}_${version}_${arch}.deb"
  
  # Create a minimal dummy .deb file (canonical name)
  touch "$TEST_DIR/packages/$canonical_name"

  # Create metadata file
  cat > "$TEST_DIR/packages/${canonical_name}.meta" <<METAEOF
package=$package_name
version=$version
architecture=$arch
distro=$distro
component=$component
original_filename=${package_name}_${version}_${arch}+${distro}+${component}.deb
METAEOF
}

# ============================================================================
# Test 1: Full rebuild with mixed package types
# ============================================================================
test_case "Full rebuild mode: trixie-specific pkg should NOT appear in bookworm"

mkdir -p "$TEST_DIR/packages"
mkdir -p "$TEST_DIR/apt-repo"
cd "$TEST_DIR"

# Create test packages
create_test_package "signalk" "2.17.2-1" "all" "trixie" "main"
create_test_package "cockpit-apt" "0.2.0-1" "all" "bookworm" "main"

echo "Scenario: Full rebuild processes trixie-stable channel"
echo "- signalk is trixie-specific"
echo "- cockpit-apt is bookworm-specific"
echo ""
echo "Problem: Full rebuild naively copies all downloaded packages to the distribution being processed"
echo "Result: Both packages end up in trixie-stable (WRONG)"
echo ""

# Simulate what the current full rebuild does (WRONG):
mkdir -p "$TEST_DIR/apt-repo/pool/trixie-stable/main"
cp "$TEST_DIR/packages"/*.deb "$TEST_DIR/apt-repo/pool/trixie-stable/main/"

# What we expect: signalk should be there, cockpit-apt should NOT
assert_file_exists "$TEST_DIR/apt-repo/pool/trixie-stable/main/signalk_2.17.2-1_all.deb" \
  "signalk_trixie is correctly in trixie-stable"

assert_file_exists "$TEST_DIR/apt-repo/pool/trixie-stable/main/cockpit-apt_0.2.0-1_all.deb" \
  "cockpit-apt_bookworm is IN trixie-stable (WRONG - this is the bug)"

# What should happen with correct routing:
echo ""
echo "With correct routing:"

rm -rf "$TEST_DIR/apt-repo"
mkdir -p "$TEST_DIR/apt-repo"

# Use the route_package function properly
route_package "$TEST_DIR/packages/signalk_2.17.2-1_all.deb" "stable" "$TEST_DIR"
route_package "$TEST_DIR/packages/cockpit-apt_0.2.0-1_all.deb" "stable" "$TEST_DIR"

assert_file_exists "$TEST_DIR/apt-repo/pool/trixie-stable/main/signalk_2.17.2-1_all.deb" \
  "signalk is in trixie-stable (CORRECT)"

assert_file_exists "$TEST_DIR/apt-repo/pool/bookworm-stable/main/cockpit-apt_0.2.0-1_all.deb" \
  "cockpit-apt is in bookworm-stable (CORRECT)"

assert_file_not_exists "$TEST_DIR/apt-repo/pool/trixie-stable/main/cockpit-apt_0.2.0-1_all.deb" \
  "cockpit-apt is NOT in trixie-stable (CORRECT)"

# ============================================================================
# Test 2: distro=any should expand across all distributions
# ============================================================================
test_case "Full rebuild mode: distro=any should expand to all distributions"

rm -rf "$TEST_DIR/apt-repo"
mkdir -p "$TEST_DIR/apt-repo"

create_test_package "halpi2-daemon" "1.0.0-1" "all" "any" "hatlabs"

echo "Scenario: halpi2-daemon with distro=any should be in:"
echo "  - pool/stable/main (legacy)"
echo "  - pool/bookworm-stable/hatlabs"
echo "  - pool/trixie-stable/hatlabs"
echo "  - pool/forky-stable/hatlabs"
echo ""

route_package "$TEST_DIR/packages/halpi2-daemon_1.0.0-1_all.deb" "stable" "$TEST_DIR"

assert_file_exists "$TEST_DIR/apt-repo/pool/stable/main/halpi2-daemon_1.0.0-1_all.deb" \
  "halpi2-daemon in legacy stable/main"

assert_file_exists "$TEST_DIR/apt-repo/pool/bookworm-stable/hatlabs/halpi2-daemon_1.0.0-1_all.deb" \
  "halpi2-daemon in bookworm-stable/hatlabs"

assert_file_exists "$TEST_DIR/apt-repo/pool/trixie-stable/hatlabs/halpi2-daemon_1.0.0-1_all.deb" \
  "halpi2-daemon in trixie-stable/hatlabs"

assert_file_exists "$TEST_DIR/apt-repo/pool/forky-stable/hatlabs/halpi2-daemon_1.0.0-1_all.deb" \
  "halpi2-daemon in forky-stable/hatlabs"

# ============================================================================
# Test 3: Component preservation
# ============================================================================
test_case "Full rebuild mode: component metadata should be preserved"

rm -rf "$TEST_DIR/apt-repo"
mkdir -p "$TEST_DIR/apt-repo"

create_test_package "pkg-main" "1.0-1" "all" "any" "main"
create_test_package "pkg-hatlabs" "1.0-1" "all" "any" "hatlabs"

route_package "$TEST_DIR/packages/pkg-main_1.0-1_all.deb" "stable" "$TEST_DIR"
route_package "$TEST_DIR/packages/pkg-hatlabs_1.0-1_all.deb" "stable" "$TEST_DIR"

# pkg-main should NOT be in legacy stable/main (only hatlabs goes there)
assert_file_not_exists "$TEST_DIR/apt-repo/pool/stable/main/pkg-main_1.0-1_all.deb" \
  "pkg-main is NOT in legacy stable/main (correct - no legacy for main)"

# pkg-main should be in distro-specific main
assert_file_exists "$TEST_DIR/apt-repo/pool/trixie-stable/main/pkg-main_1.0-1_all.deb" \
  "pkg-main is in trixie-stable/main (correct)"

# pkg-hatlabs should be in legacy AND distro-specific
assert_file_exists "$TEST_DIR/apt-repo/pool/stable/main/pkg-hatlabs_1.0-1_all.deb" \
  "pkg-hatlabs is in legacy stable/main (correct - legacy routing)"

assert_file_exists "$TEST_DIR/apt-repo/pool/trixie-stable/hatlabs/pkg-hatlabs_1.0-1_all.deb" \
  "pkg-hatlabs is in trixie-stable/hatlabs (correct)"

print_summary
