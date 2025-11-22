#!/bin/bash
# Routing functions for package distribution
# These functions are sourced by both the workflow and test scripts

# List of supported distributions (easily extensible for future distros)
# Note: This list includes only actual distributions, not "any" (which is an alias)
# See suffix-parsing-functions.sh for VALID_DISTROS which includes "any" for validation
SUPPORTED_DISTROS=("bookworm" "trixie")

# route_package - Route a package to appropriate pools based on metadata
#
# Usage: route_package <package_file> <channel> [apt_repo_dir]
#
# Routes a package to distribution pools based on its distro and component suffix.
# Handles distro expansion for distro=any and legacy routing for Hat Labs packages.
#
# Arguments:
#   package_file - Path to the .deb package file (e.g., "packages/halpi2-daemon_1.0.0-1_all.deb")
#   channel - Release channel: "stable" or "unstable"
#   apt_repo_dir - Base directory for apt-repo (default: "apt-repo")
#
# Reads metadata from: ${package_file}.meta
#   Expected format:
#     package=<name>
#     version=<version>
#     architecture=<arch>
#     distro=<distro>
#     component=<component>
#     original_filename=<name>
#
# Returns:
#   0 on success
#   1 if metadata file not found or invalid
#
# Examples:
#   # Route a package with default apt-repo location
#   route_package "packages/halpi2-daemon_1.0.0-1_all.deb" "stable"
#
#   # Route a package with custom apt-repo location (for testing)
#   route_package "packages/pkg.deb" "stable" "/tmp/apt-repo"
#
route_package() {
  local package_file="$1"
  local channel="$2"
  local apt_repo_dir="${3:-.}/apt-repo"

  # Validate channel
  if [[ ! "$channel" =~ ^(stable|unstable)$ ]]; then
    echo "Error: Invalid channel '$channel' (must be 'stable' or 'unstable')" >&2
    return 1
  fi

  # Get package filename (without path)
  local filename=$(basename "$package_file")

  # Read metadata file (required - no fallback for backward compatibility)
  local meta_file="${package_file}.meta"
  if [ ! -f "$meta_file" ]; then
    echo "Error: Metadata file not found: $meta_file" >&2
    echo "  Package requires suffix parsing first (Issue #29)" >&2
    return 1
  fi

  # Parse metadata
  local distro component
  source "$meta_file" 2>/dev/null || {
    echo "Error: Failed to read metadata from $meta_file" >&2
    return 1
  }

  # Validate we have required fields
  if [ -z "$distro" ] || [ -z "$component" ]; then
    echo "Error: Metadata missing distro or component" >&2
    return 1
  fi

  # Determine target distributions
  local target_distros
  if [ "$distro" = "any" ]; then
    # Expand to all supported distributions
    target_distros=("${SUPPORTED_DISTROS[@]}")
  else
    # Single specific distribution
    target_distros=("$distro")
  fi

  # Route package to each target distribution
  for target_distro in "${target_distros[@]}"; do
    local target_dist="${target_distro}-${channel}"
    local target_pool="$apt_repo_dir/pool/${target_dist}/${component}"

    # Create directory
    mkdir -p "$target_pool"

    # Copy package
    cp "$package_file" "$target_pool/$filename"
  done

  # Legacy routing: if distro=any AND component=hatlabs
  if [ "$distro" = "any" ] && [ "$component" = "hatlabs" ]; then
    local legacy_pool="$apt_repo_dir/pool/${channel}/main"
    mkdir -p "$legacy_pool"
    cp "$package_file" "$legacy_pool/$filename"
  fi

  return 0
}
