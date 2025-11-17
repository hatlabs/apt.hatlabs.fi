#!/bin/bash
# Test script for routing logic functionality
# Tests the route_package and related routing functions

# Note: Don't use set -e because some functions return non-zero for test purposes

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counters
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

# Source the routing functions
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/routing-functions.sh"

# Create temporary test directory
TEST_DIR=$(mktemp -d)
trap "rm -rf $TEST_DIR" EXIT

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

  # Trim whitespace from actual value
  actual=$(echo "$actual" | xargs)

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

count_files() {
  local pattern="$1"
  # Only count files in apt-repo, not in packages directory (source)
  find "$TEST_DIR/apt-repo" -type f -path "$pattern" 2>/dev/null | wc -l
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

# Helper function to create test package and metadata
create_test_package() {
  local package_name="$1"
  local distro="$2"
  local component="$3"
  local channel="$4"

  # Create a minimal dummy .deb file
  touch "$TEST_DIR/packages/${package_name}.deb"

  # Create metadata file
  cat > "$TEST_DIR/packages/${package_name}.deb.meta" <<EOF
package=$package_name
version=1.0.0-1
architecture=all
distro=$distro
component=$component
original_filename=${package_name}+${distro}+${component}.deb
EOF
}

# ============================================================================
# Test 1: Route distro=any, component=hatlabs (legacy routing)
# ============================================================================
test_case "Route distro=any, component=hatlabs to 4 locations"

mkdir -p "$TEST_DIR/packages"
mkdir -p "$TEST_DIR/apt-repo"
cd "$TEST_DIR"

create_test_package "halpi2-daemon_1.0.0-1_all" "any" "hatlabs"

# Call routing function
route_package "packages/halpi2-daemon_1.0.0-1_all.deb" "stable" "$TEST_DIR"

# Verify package appears in 4 locations
assert_file_exists "$TEST_DIR/apt-repo/pool/stable/main/halpi2-daemon_1.0.0-1_all.deb" \
  "Package routed to legacy stable/main"
assert_file_exists "$TEST_DIR/apt-repo/pool/bookworm-stable/hatlabs/halpi2-daemon_1.0.0-1_all.deb" \
  "Package routed to bookworm-stable/hatlabs"
assert_file_exists "$TEST_DIR/apt-repo/pool/trixie-stable/hatlabs/halpi2-daemon_1.0.0-1_all.deb" \
  "Package routed to trixie-stable/hatlabs"
assert_file_exists "$TEST_DIR/apt-repo/pool/forky-stable/hatlabs/halpi2-daemon_1.0.0-1_all.deb" \
  "Package routed to forky-stable/hatlabs"

# Count total copies
count=$(count_files "**/halpi2-daemon_1.0.0-1_all.deb")
assert_equals "4" "$count" "Package copied to exactly 4 locations"

# ============================================================================
# Test 2: Route distro=trixie, component=main (single location)
# ============================================================================
test_case "Route distro=trixie, component=main to 1 location"

rm -rf "$TEST_DIR/apt-repo"
mkdir -p "$TEST_DIR/apt-repo"

create_test_package "signalk_2.17.2-1_all" "trixie" "main"

route_package "packages/signalk_2.17.2-1_all.deb" "stable" "$TEST_DIR"

assert_file_exists "$TEST_DIR/apt-repo/pool/trixie-stable/main/signalk_2.17.2-1_all.deb" \
  "Package routed to trixie-stable/main"
assert_file_not_exists "$TEST_DIR/apt-repo/pool/stable/main/signalk_2.17.2-1_all.deb" \
  "Package NOT routed to legacy stable/main"

count=$(count_files "**/signalk_2.17.2-1_all.deb")
assert_equals "1" "$count" "Package copied to exactly 1 location"

# ============================================================================
# Test 3: Route distro=any, component=main (3 locations, no legacy)
# ============================================================================
test_case "Route distro=any, component=main to 3 locations (no legacy)"

rm -rf "$TEST_DIR/apt-repo"
mkdir -p "$TEST_DIR/apt-repo"

create_test_package "runtipi_1.0-1_all" "any" "main"

route_package "packages/runtipi_1.0-1_all.deb" "stable" "$TEST_DIR"

assert_file_exists "$TEST_DIR/apt-repo/pool/bookworm-stable/main/runtipi_1.0-1_all.deb" \
  "Package routed to bookworm-stable/main"
assert_file_exists "$TEST_DIR/apt-repo/pool/trixie-stable/main/runtipi_1.0-1_all.deb" \
  "Package routed to trixie-stable/main"
assert_file_exists "$TEST_DIR/apt-repo/pool/forky-stable/main/runtipi_1.0-1_all.deb" \
  "Package routed to forky-stable/main"
assert_file_not_exists "$TEST_DIR/apt-repo/pool/stable/main/runtipi_1.0-1_all.deb" \
  "Package NOT routed to legacy stable/main"

count=$(count_files "**/runtipi_1.0-1_all.deb")
assert_equals "3" "$count" "Package copied to exactly 3 locations"

# ============================================================================
# Test 4: Route unstable channel (pre-release)
# ============================================================================
test_case "Route distro=trixie, component=main with unstable channel"

rm -rf "$TEST_DIR/apt-repo"
mkdir -p "$TEST_DIR/apt-repo"

create_test_package "cockpit-apt_0.2.0-1_all" "trixie" "main"

route_package "packages/cockpit-apt_0.2.0-1_all.deb" "unstable" "$TEST_DIR"

assert_file_exists "$TEST_DIR/apt-repo/pool/trixie-unstable/main/cockpit-apt_0.2.0-1_all.deb" \
  "Package routed to trixie-unstable/main"
assert_file_not_exists "$TEST_DIR/apt-repo/pool/trixie-stable/main/cockpit-apt_0.2.0-1_all.deb" \
  "Package NOT in stable channel"

# ============================================================================
# Test 5: Legacy routing with unstable channel
# ============================================================================
test_case "Route distro=any, component=hatlabs with unstable channel"

rm -rf "$TEST_DIR/apt-repo"
mkdir -p "$TEST_DIR/apt-repo"

create_test_package "halpi2-firmware_2.0-1_all" "any" "hatlabs"

route_package "packages/halpi2-firmware_2.0-1_all.deb" "unstable" "$TEST_DIR"

assert_file_exists "$TEST_DIR/apt-repo/pool/unstable/main/halpi2-firmware_2.0-1_all.deb" \
  "Package routed to legacy unstable/main"
assert_file_exists "$TEST_DIR/apt-repo/pool/trixie-unstable/hatlabs/halpi2-firmware_2.0-1_all.deb" \
  "Package routed to trixie-unstable/hatlabs"

count=$(count_files "**/halpi2-firmware_2.0-1_all.deb")
assert_equals "4" "$count" "Package copied to 4 locations (1 legacy + 3 distro-specific)"

# ============================================================================
# Test 6: Missing metadata file (should handle gracefully)
# ============================================================================
test_case "Handle missing metadata file gracefully"

rm -rf "$TEST_DIR/apt-repo"
mkdir -p "$TEST_DIR/apt-repo"

# Create package but NO metadata
touch "$TEST_DIR/packages/orphan_1.0-1_all.deb"

# Call routing function - should fail gracefully or use fallback
route_package "packages/orphan_1.0-1_all.deb" "stable" "$TEST_DIR" 2>/dev/null
result=$?

if [ $result -ne 0 ]; then
  echo -e "${GREEN}✓ PASS${NC}: Function handles missing metadata gracefully"
  TESTS_PASSED=$((TESTS_PASSED + 1))
else
  echo -e "${RED}✗ FAIL${NC}: Function should handle missing metadata"
  TESTS_FAILED=$((TESTS_FAILED + 1))
fi

# ============================================================================
# Test 7: Bookworm specific package
# ============================================================================
test_case "Route distro=bookworm, component=main"

rm -rf "$TEST_DIR/apt-repo"
mkdir -p "$TEST_DIR/apt-repo"

create_test_package "package_1.0-1_all" "bookworm" "main"

route_package "packages/package_1.0-1_all.deb" "stable" "$TEST_DIR"

assert_file_exists "$TEST_DIR/apt-repo/pool/bookworm-stable/main/package_1.0-1_all.deb" \
  "Package routed to bookworm-stable/main"

count=$(count_files "**/package_1.0-1_all.deb")
assert_equals "1" "$count" "Package copied to exactly 1 location"

# ============================================================================
# Test 8: Forky distribution (future distro)
# ============================================================================
test_case "Route distro=forky, component=main (future support)"

rm -rf "$TEST_DIR/apt-repo"
mkdir -p "$TEST_DIR/apt-repo"

create_test_package "future_1.0-1_all" "forky" "main"

route_package "packages/future_1.0-1_all.deb" "stable" "$TEST_DIR"

assert_file_exists "$TEST_DIR/apt-repo/pool/forky-stable/main/future_1.0-1_all.deb" \
  "Package routed to forky-stable/main"

# ============================================================================
# Test 9: Multiple packages routed together
# ============================================================================
test_case "Route multiple packages correctly"

rm -rf "$TEST_DIR/apt-repo"
mkdir -p "$TEST_DIR/apt-repo"

create_test_package "pkg1_1.0-1_all" "any" "hatlabs"
create_test_package "pkg2_2.0-1_all" "trixie" "main"
create_test_package "pkg3_3.0-1_all" "any" "main"

route_package "packages/pkg1_1.0-1_all.deb" "stable" "$TEST_DIR"
route_package "packages/pkg2_2.0-1_all.deb" "stable" "$TEST_DIR"
route_package "packages/pkg3_3.0-1_all.deb" "stable" "$TEST_DIR"

# pkg1: 4 locations (legacy + 3 distro-specific)
pkg1_count=$(count_files "**/pkg1_1.0-1_all.deb")
assert_equals "4" "$pkg1_count" "pkg1 (any/hatlabs) copied to 4 locations"

# pkg2: 1 location (trixie-specific)
pkg2_count=$(count_files "**/pkg2_2.0-1_all.deb")
assert_equals "1" "$pkg2_count" "pkg2 (trixie/main) copied to 1 location"

# pkg3: 3 locations (no legacy for non-hatlabs)
pkg3_count=$(count_files "**/pkg3_3.0-1_all.deb")
assert_equals "3" "$pkg3_count" "pkg3 (any/main) copied to 3 locations"

# ============================================================================
# Test 10: Directory creation
# ============================================================================
test_case "Verify directory structure created correctly"

rm -rf "$TEST_DIR/apt-repo"
mkdir -p "$TEST_DIR/apt-repo"

create_test_package "test_1.0-1_all" "any" "hatlabs"
route_package "packages/test_1.0-1_all.deb" "stable" "$TEST_DIR"

# Check all expected directories exist
expected_dirs=(
  "apt-repo/pool/stable/main"
  "apt-repo/pool/bookworm-stable/hatlabs"
  "apt-repo/pool/trixie-stable/hatlabs"
  "apt-repo/pool/forky-stable/hatlabs"
)

all_dirs_exist=true
for dir in "${expected_dirs[@]}"; do
  if [ ! -d "$TEST_DIR/$dir" ]; then
    echo "  Missing: $dir"
    all_dirs_exist=false
  fi
done

if [ "$all_dirs_exist" = true ]; then
  echo -e "${GREEN}✓ PASS${NC}: All expected directories created"
  TESTS_PASSED=$((TESTS_PASSED + 1))
else
  echo -e "${RED}✗ FAIL${NC}: Some directories missing"
  TESTS_FAILED=$((TESTS_FAILED + 1))
fi

# Print summary
print_summary
