# APT Repository Component Structure

**Status:** ✅ Fully Implemented

This document describes how the APT repository handles multiple components (main, hatlabs) and how to use them.

## Overview

The Hat Labs APT repository supports multiple **components** which allow users to selectively enable/disable package categories. This enables:

- Users to add only the components they need
- Separation of Hat Labs products from general marine applications
- Flexibility for future expansion (contrib, non-free, etc.)

## Components

### Current Components

- **main** - General packages (third-party marine applications, utilities)
- **hatlabs** - Hat Labs product packages (HALPI2 daemon, firmware, etc.)

### Adding New Components

To add new components:

1. Update `scripts/suffix-parsing-functions.sh` - Add to `VALID_COMPONENTS` array
2. Update `.github/workflows/update-repo.yml` - Add to loop (line 441)
3. Update package metadata to include the new component in filename suffix

## Repository Structure

### Pool Organization

Packages are stored in distribution and component-specific subdirectories:

```
apt-repo/pool/
├── stable/main/                    # Legacy (Hat Labs products only)
├── unstable/main/                  # Legacy (Hat Labs products only)
├── bookworm-stable/
│   ├── main/                       # General packages for Bookworm stable
│   └── hatlabs/                    # Hat Labs products for Bookworm stable
├── bookworm-unstable/
│   ├── main/
│   └── hatlabs/
├── trixie-stable/
│   ├── main/
│   └── hatlabs/
└── trixie-unstable/
    ├── main/
    └── hatlabs/
```

**How It Works:**
1. Each package's filename includes routing metadata: `{package}_{version}_{arch}+{distro}+{component}.deb`
2. During download, canonical names are extracted: `{package}_{version}_{arch}.deb`
3. Metadata is stored in `.meta` files alongside packages
4. Routing logic copies packages to correct pool directories based on component metadata

### Metadata Organization

Separate Packages files are generated for each component:

```
apt-repo/dists/trixie-stable/
├── main/
│   ├── binary-arm64/
│   │   ├── Packages          # Packages in main component (arm64)
│   │   └── Packages.gz
│   └── binary-all/
│       ├── Packages          # Packages in main component (all architectures)
│       └── Packages.gz
└── hatlabs/
    ├── binary-arm64/
    │   ├── Packages          # Packages in hatlabs component (arm64)
    │   └── Packages.gz
    └── binary-all/
        ├── Packages          # Packages in hatlabs component (all architectures)
        └── Packages.gz
```

**Single Release File Per Distribution:**

- `dists/trixie-stable/Release` - Lists all components and includes checksums for all Packages files
- `dists/trixie-stable/Release.gpg` - Detached signature
- `dists/trixie-stable/InRelease` - Inline-signed release file

Example Release file excerpt:
```
Components: main hatlabs
Architectures: arm64 all

MD5Sum:
 <hash> 1234 main/binary-arm64/Packages
 <hash> 2345 main/binary-arm64/Packages.gz
 <hash> 3456 hatlabs/binary-arm64/Packages
 <hash> 4567 hatlabs/binary-arm64/Packages.gz
```

## Using Components in APT

### View Available Components

Check the Release file to see which components are available:

```bash
curl https://apt.hatlabs.fi/dists/trixie-stable/Release
# Look for: Components: main hatlabs
```

### Add Repository with Specific Components

Users can selectively enable components:

```bash
# Add GPG key
curl -fsSL https://apt.hatlabs.fi/hat-labs-apt-key.asc | \
  sudo gpg --dearmor -o /usr/share/keyrings/hatlabs.gpg

# Add repository with only main component
echo "deb [signed-by=/usr/share/keyrings/hatlabs.gpg] https://apt.hatlabs.fi trixie-stable main" | \
  sudo tee /etc/apt/sources.list.d/hatlabs.list

# Or include both components
echo "deb [signed-by=/usr/share/keyrings/hatlabs.gpg] https://apt.hatlabs.fi trixie-stable main hatlabs" | \
  sudo tee /etc/apt/sources.list.d/hatlabs.list
```

### Update and Install

```bash
sudo apt update
sudo apt install package-name
```

## Workflow Process

### Download Phase

1. Packages are downloaded from source repositories
2. Metadata is extracted from `.deb` control files
3. Package filenames are normalized to canonical format
4. Routing metadata (distro, component) is stored in `.meta` files

### Routing Phase

1. For each channel (stable, unstable):
   - Packages are read with their metadata
   - Distro expansion is applied (distro=any → all distributions)
   - Packages are copied to appropriate pool directories based on component
   - Legacy routing is applied for Hat Labs packages (distro=any + component=hatlabs)

### Build Phase

1. For each distribution:
   - For each component that has packages:
     - `dpkg-scanpackages` is run separately for arm64 and all architectures
     - Separate Packages files are generated
   - Release file is generated listing all components
   - Release file is cryptographically signed

## Implementation Details

### Routing Logic (routing-functions.sh)

The `route_package()` function:
- Reads metadata from `.meta` files
- Expands `distro=any` to all supported distributions
- Routes packages to `pool/{distro}-{channel}/{component}/`
- Applies legacy routing for Hat Labs packages

### Component Discovery (update-repo.yml)

The `build_release()` function:
- Searches for Packages files in `dists/{dist}/{component}/binary-{arch}/`
- Only includes components that have actual packages
- Lists all discovered components in Release file
- Generates checksums for all component-specific Packages files

## Acceptance Criteria - Implementation Status

- ✅ Pool directories created with component subdirectories
- ✅ Packages files generated per component
- ✅ Release files include all components
- ✅ Users can selectively add components to APT sources

## Related Documentation

- [ARCHITECTURE.md](ARCHITECTURE.md) - System architecture and design decisions
- [SPEC.md](SPEC.md) - Technical specification
- [Extended Naming Convention](ARCHITECTURE.md#extended-naming-convention) - Filename format for routing

## See Also

- GitHub Issue #28 - Original multi-distribution design
- GitHub Issue #33 - Component structure implementation (this feature)
- GitHub PR #45 - Canonical filename normalization with component routing
