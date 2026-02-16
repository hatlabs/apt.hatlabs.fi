#!/bin/bash
# APT repository metadata build functions
# Sourced by the update-repo workflow to build Packages/Release files.
# Requires: $GPG_KEY_ID set in environment, working directory inside apt-repo/

# build_component - Generate Packages index files for a distribution/component
#
# Usage: build_component <dist> <component>
#
# Must be called from the apt-repo directory.
# Scans pool/<dist>/<component>/*.deb and generates Packages + Packages.gz
# for each architecture in dists/<dist>/<component>/binary-<arch>/.
#
build_component() {
  local dist=$1
  local component=$2

  echo "=== Building distribution: $dist/$component ==="

  local dist_path="dists/$dist"
  local comp_path="$dist_path/$component"
  local pool_path="pool/$dist/$component"

  if [ ! -d "$pool_path" ]; then
    echo "Pool directory pool/$dist/$component does not exist - skipping"
    return 0
  fi

  if ! ls "$pool_path"/*.deb 1>/dev/null 2>&1; then
    echo "No .deb packages in pool/$dist/$component - skipping"
    return 0
  fi

  mkdir -p "$comp_path/binary-arm64"
  mkdir -p "$comp_path/binary-armhf"
  mkdir -p "$comp_path/binary-all"

  echo "Generating Packages files..."

  dpkg-scanpackages -a arm64 "$pool_path" /dev/null > "$comp_path/binary-arm64/Packages" 2>/dev/null || touch "$comp_path/binary-arm64/Packages"
  gzip -kf "$comp_path/binary-arm64/Packages"

  dpkg-scanpackages -a armhf "$pool_path" /dev/null > "$comp_path/binary-armhf/Packages" 2>/dev/null || touch "$comp_path/binary-armhf/Packages"
  gzip -kf "$comp_path/binary-armhf/Packages"

  dpkg-scanpackages -a all "$pool_path" /dev/null > "$comp_path/binary-all/Packages" 2>/dev/null || touch "$comp_path/binary-all/Packages"
  gzip -kf "$comp_path/binary-all/Packages"

  echo "Built $dist/$component"
}

# build_release - Generate signed Release/InRelease files for a distribution
#
# Usage: build_release <dist>
#
# Must be called from the apt-repo directory.
# Requires $GPG_KEY_ID set in the environment.
#
build_release() {
  local dist=$1

  echo "=== Generating Release file for $dist ==="

  local dist_path="dists/$dist"

  # Find components that have been built (have Packages files)
  # Only include known components (main, hatlabs)
  local components=""
  for comp in main hatlabs; do
    if [ -f "$dist_path/$comp/binary-arm64/Packages" ] || [ -f "$dist_path/$comp/binary-armhf/Packages" ] || [ -f "$dist_path/$comp/binary-all/Packages" ]; then
      components="$components $comp"
    fi
  done
  components=$(echo "$components" | xargs)

  # Default to main component if no packages found
  if [ -z "$components" ]; then
    echo "No packages in $dist, creating empty main component"
    components="main"
    mkdir -p "$dist_path/main/binary-arm64"
    mkdir -p "$dist_path/main/binary-armhf"
    mkdir -p "$dist_path/main/binary-all"
    touch "$dist_path/main/binary-arm64/Packages"
    touch "$dist_path/main/binary-armhf/Packages"
    touch "$dist_path/main/binary-all/Packages"
    gzip -kf "$dist_path/main/binary-arm64/Packages"
    gzip -kf "$dist_path/main/binary-armhf/Packages"
    gzip -kf "$dist_path/main/binary-all/Packages"
  fi

  # Determine suite and description based on distribution pattern
  if [[ "$dist" == "stable" ]]; then
    SUITE="stable"
    CODENAME="stable"
    DESC="Hat Labs product packages (stable)"
  elif [[ "$dist" == "unstable" ]]; then
    SUITE="unstable"
    CODENAME="unstable"
    DESC="Hat Labs product packages (unstable - rolling)"
  elif [[ "$dist" =~ ^([a-z0-9]+)-(stable|unstable)$ ]]; then
    CODENAME="${BASH_REMATCH[1]}"
    STABILITY="${BASH_REMATCH[2]}"
    SUITE="$dist"
    CODENAME_DISPLAY="$(echo ${CODENAME:0:1} | tr '[:lower:]' '[:upper:]')${CODENAME:1}"
    if [[ "$STABILITY" == "stable" ]]; then
      DESC="Hat Labs packages for Debian $CODENAME_DISPLAY (stable)"
    else
      DESC="Hat Labs packages for Debian $CODENAME_DISPLAY (unstable - rolling)"
    fi
  else
    SUITE="$dist"
    CODENAME="$dist"
    DESC="Hat Labs APT Repository - $dist"
  fi

  cd "$dist_path"

  cat > Release << EOF
Origin: Hat Labs
Label: Hat Labs APT Repository
Suite: $SUITE
Codename: $CODENAME
Version: 1.0
Architectures: arm64 armhf all
Components: $components
Description: $DESC
Date: $(date -Ru)
EOF

  apt-ftparchive release . >> Release

  echo "Signing Release file..."
  gpg --batch --yes --detach-sign --armor -u $GPG_KEY_ID -o Release.gpg Release
  gpg --batch --yes --clear-sign -u $GPG_KEY_ID -o InRelease Release

  cd ../..
  echo "Generated Release file for $dist"
}
