#!/bin/bash
# Suffix parsing functions for package routing
# These functions are sourced by both the workflow and test scripts

# List of valid distributions and components
VALID_DISTROS=("any" "bookworm" "trixie" "forky")
VALID_COMPONENTS=("main" "hatlabs")

# parse_package_suffix - Extract distro and component from package filename
#
# Usage: parse_package_suffix <filename> <distro_var> <component_var>
#
# Parses the extended naming convention: package_version_arch+distro+component.deb
# If suffix is not found, falls back to defaults: distro=any, component=main
#
# Arguments:
#   filename - Package filename to parse
#   distro_var - Name of variable to store distro result
#   component_var - Name of variable to store component result
#
# Returns:
#   0 if suffix was successfully parsed
#   1 if no suffix found (fallback applied)
#
# Example:
#   parse_package_suffix "halpi2-daemon_1.0.0-1_all+any+hatlabs.deb" distro component
#   # distro="any", component="hatlabs"
#
parse_package_suffix() {
  local filename="$1"
  local distro_var="$2"
  local component_var="$3"

  # Try to parse suffix: +distro+component.deb
  # Regex explanation:
  # [+] - literal plus sign (character class for compatibility)
  # ([a-z]+) - capture group 1: one or more lowercase letters (distro)
  # [+] - literal plus sign (character class for compatibility)
  # ([a-z]+) - capture group 2: one or more lowercase letters (component)
  # \.deb$ - ends with .deb
  if [[ "$filename" =~ [+]([a-z]+)[+]([a-z]+)\.deb$ ]]; then
    eval "$distro_var=\"${BASH_REMATCH[1]}\""
    eval "$component_var=\"${BASH_REMATCH[2]}\""
    return 0
  else
    # No suffix found - use defaults
    # Temporary: default to hatlabs component to avoid breaking production stable/main
    # Once all packages have proper distro+component suffixes, this will change to main
    eval "$distro_var=\"any\""
    eval "$component_var=\"hatlabs\""
    return 1
  fi
}

# validate_suffix - Validate parsed distro and component values
#
# Usage: validate_suffix <distro> <component>
#
# Checks if distro and component are in the list of valid values.
# Outputs warnings for invalid values.
#
# Arguments:
#   distro - Distribution name to validate
#   component - Component name to validate
#
# Returns:
#   0 if both distro and component are valid
#   1 if either distro or component is invalid
#
# Example:
#   if validate_suffix "trixie" "main"; then
#     echo "Valid"
#   else
#     echo "Invalid - fallback needed"
#   fi
#
validate_suffix() {
  local distro="$1"
  local component="$2"
  local valid=0

  # Check if distro is in valid list
  if [[ ! " ${VALID_DISTROS[@]} " =~ " ${distro} " ]]; then
    echo "⚠️  Warning: Unknown distro '$distro' (valid: ${VALID_DISTROS[*]})" >&2
    valid=1
  fi

  # Check if component is in valid list
  if [[ ! " ${VALID_COMPONENTS[@]} " =~ " ${component} " ]]; then
    echo "⚠️  Warning: Unknown component '$component' (valid: ${VALID_COMPONENTS[*]})" >&2
    valid=1
  fi

  return $valid
}
