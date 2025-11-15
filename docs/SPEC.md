# Technical Specification: Multi-Distribution APT Repository

## Project Overview

The Hat Labs APT repository serves packages for multiple product lines with different upstream distribution dependencies and stability requirements. This specification defines a multi-distribution repository architecture that supports both distro-agnostic packages (HALPI2 hardware support) and distro-specific packages (Halos operating system components).

## Goals

1. Support multiple upstream Debian/Raspberry Pi OS distributions (currently Bookworm and Trixie)
2. Provide both stable and unstable package channels for all products
3. Maintain backward compatibility with existing Hat Labs product package installations
4. Enable rolling release workflows with different gating strategies (stable vs unstable)
5. Keep Hat Labs product and Halos packages organizationally separate while sharing infrastructure

## Distribution Naming Scheme

### Hat Labs Product Packages (Distro-Agnostic)

Hat Labs product packages contain firmware files and statically-linked binaries that work across multiple upstream distributions. These use Debian-style stability naming:

- **stable** - Gated releases via GitHub release workflow. This is the existing distribution and must remain for backward compatibility.
- **unstable** - Rolling releases tracking the main branch. Updated on every merge.

### Halos Packages (Distro-Specific)

Halos packages depend on specific upstream Debian/Raspberry Pi OS releases and require appropriate build environments. Distribution names explicitly encode both the upstream distro and stability level:

- **bookworm-stable** - Halos stable packages for Debian Bookworm
- **bookworm-unstable** - Halos rolling packages for Debian Bookworm
- **trixie-stable** - Halos stable packages for Debian Trixie
- **trixie-unstable** - Halos rolling packages for Debian Trixie

Additional upstream distributions can be added following this pattern (e.g., forky-stable, forky-unstable).

### Component Structure

All packages use the **main** component. Future expansion may include additional components:

- **main** - Primary packages (current use)
- **non-free** - Potential future use for packages with licensing restrictions
- **contrib** - Potential future use for packages depending on non-free components

## Channel Definitions

All repositories operate on a rolling release model with different gating mechanisms:

- **stable** - Packages released through GitHub's release workflow. These go through a gating process (manual release creation, version tagging) before being published to the APT repository.
- **unstable** - Typically packages automatically published on every merge to the main branch. For most repos, these receive no additional gating beyond CI/CD checks.

Both stable and unstable channels roll forward continuously - there is no concept of "frozen" releases. The difference is in the gating and release cadence.

## Workflow Dispatch Payload

Package repositories trigger APT repository updates via GitHub's repository_dispatch event. Each trigger specifies exactly what is being built through three fields:

### Payload Fields

**distro** - The upstream distribution being targeted
- `bookworm` - Debian Bookworm / Raspberry Pi OS Bookworm
- `trixie` - Debian Trixie / Raspberry Pi OS Trixie
- `any` - Distro-agnostic packages (Hat Labs product packages)

**channel** - The release channel
- `stable` - Gated releases
- `unstable` - Rolling main branch

**component** - The package component
- `main` - Primary component (default)
- Additional components as needed in the future

### Distribution Name Construction

The APT repository workflow constructs distribution names from payload fields:

- When distro is "any": distribution name = channel value (e.g., "stable", "unstable")
- When distro is specific: distribution name = distro-channel (e.g., "bookworm-stable", "trixie-unstable")

### Example Payloads

HALPI2 firmware stable release:
```json
{
  "distro": "any",
  "channel": "stable",
  "component": "main"
}
```
Result: Package added to `dists/stable/main/`

Halos unstable build for Trixie:
```json
{
  "distro": "trixie",
  "channel": "unstable",
  "component": "main"
}
```
Result: Package added to `dists/trixie-unstable/main/`

## User Experience

### Source List Configuration

In most cases, APT sources are pre-configured in the image. However, users may need to manually add sources for specific use cases.
Users configure APT sources based on their needs:

**Hat Labs product hardware support (stable only)**
```
deb [signed-by=/usr/share/keyrings/hatlabs.gpg] https://apt.hatlabs.fi stable main
```

**Hat Labs product with bleeding-edge updates**
```
deb [signed-by=/usr/share/keyrings/hatlabs.gpg] https://apt.hatlabs.fi stable main
deb [signed-by=/usr/share/keyrings/hatlabs.gpg] https://apt.hatlabs.fi unstable main
```

**Halos on Bookworm (stable packages only)**
```
deb [signed-by=/usr/share/keyrings/hatlabs.gpg] https://apt.hatlabs.fi bookworm-stable main
```

**Halos on Trixie with testing updates**
```
deb [signed-by=/usr/share/keyrings/hatlabs.gpg] https://apt.hatlabs.fi trixie-stable main
deb [signed-by=/usr/share/keyrings/hatlabs.gpg] https://apt.hatlabs.fi trixie-unstable main
```

**Complete Halos installation with HALPI2 support**
```
deb [signed-by=/usr/share/keyrings/hatlabs.gpg] https://apt.hatlabs.fi stable main
deb [signed-by=/usr/share/keyrings/hatlabs.gpg] https://apt.hatlabs.fi trixie-stable main
```

### Package Separation

Hat Labs product and Halos packages are stored in a shared package pool to avoid duplication of .deb files. Currently, all packages are visible in all distribution Packages files, meaning users can install any package from any distribution they've configured.

Users control which packages they use by:
- **Source selection**: Choosing which distributions to add to their sources.list
- **Package installation**: Explicitly installing only the packages they need

This shared-pool approach simplifies repository management and allows flexibility. Future enhancements may add per-distribution package filtering to control which packages appear in which Packages files (see ARCHITECTURE.md Future Expansion).

### Web Interface

The repository website at apt.hatlabs.fi provides a browsing interface for users to:

- **Browse distributions** - Navigate between different distributions (stable, unstable, bookworm-stable, etc.)
- **View available packages** - See all packages available in each distribution with versions and descriptions
- **Access installation instructions** - Distribution-specific setup commands for adding the repository
- **Download GPG keys** - Direct access to repository signing keys
- **View repository information** - Overview of the repository structure and purpose

The web interface should make it easy for users to discover packages and understand which distributions they need to configure for their use case.

## Package Repository Requirements

### Workflow Structure

Each package repository must implement separate workflows for:

1. **Different upstream distributions** - Bookworm and Trixie builds require different build environments and dependencies
2. **Different release channels** - Stable releases trigger on GitHub release events, unstable builds trigger on main branch merges

This typically results in four workflows for distro-specific packages:
- bookworm-stable.yml (on: release)
- bookworm-unstable.yml (on: push to main)
- trixie-stable.yml (on: release)
- trixie-unstable.yml (on: push to main)

Hat Labs product packages need only two workflows:
- stable.yml (on: release)
- unstable.yml (on: push to main)

### Build Artifacts

Package workflows must build .deb files with proper metadata:
- Package name
- Version (following semantic versioning)
- Architecture (arm64, all)
- Dependencies specific to target distribution

### Dispatch Trigger

After building packages, workflows must trigger the apt.hatlabs.fi repository update with appropriate payload fields specifying the distro, channel, and component.

## Key Constraints and Assumptions

### Backward Compatibility

The `stable/main` distribution must remain indefinitely to support existing HALPI2 installations. This distribution is never deprecated or removed.

### Architecture Support

Current focus is on ARM architectures (arm64 only) and architecture-independent packages (all). x86_64 is not in scope.

### Repository Signing

All distributions must be cryptographically signed with the Hat Labs GPG key. The signing process is uniform across all distributions.

### Build Environment Isolation

Package builds for different distributions must use appropriate build environments. Bookworm packages must not accidentally link against Trixie libraries and vice versa. This is enforced through separate workflows using distribution-appropriate build containers.

## Non-Functional Requirements

### Performance

Repository metadata updates should complete within reasonable time frames (under 10 minutes for typical package additions). Users should not experience delays when running `apt update`.

### Reliability

Repository updates must be atomic - partial updates should not leave the repository in an inconsistent state. All distribution metadata (Packages, Release, signatures) must be updated together.

### Security

All packages and repository metadata must be cryptographically signed. Users should be able to verify package authenticity through standard APT verification mechanisms.

## Out of Scope

### Not Currently Implemented

- Package version pinning or hold mechanisms (handled by APT itself)
- Package mirroring or CDN distribution (GitHub Pages is sufficient for current scale)
- Multi-architecture support beyond ARM
- Snapshot or point-in-time repository states (rolling release only)
- Package testing or validation beyond CI/CD in source repositories
- Automatic dependency resolution for multi-distribution scenarios

### Explicitly Excluded

- Creating combined "HALPI2+Halos" meta-distributions (users configure multiple sources)
- Supporting Debian releases older than Bookworm (no Bullseye support)
- Supporting non-Debian-based distributions
- Package hosting outside of apt.hatlabs.fi domain
