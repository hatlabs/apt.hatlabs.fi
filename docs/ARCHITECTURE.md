# System Architecture: Multi-Distribution APT Repository

## Overview

The Hat Labs APT repository is a GitHub Actions-based automated package repository that serves Debian packages for multiple distributions and release channels. The system receives package build notifications from source repositories, downloads the packages, and publishes them to distribution-specific repository structures hosted on GitHub Pages.

## System Components

### Repository Structure

The APT repository follows standard Debian repository layout with multiple distribution directories:

```
apt-repo/
├── pool/
│   └── main/               # All .deb files stored here
├── dists/
│   ├── stable/             # Hat Labs product packages stable channel
│   │   └── main/
│   │       ├── binary-arm64/
│   │       └── binary-all/
│   ├── unstable/           # Hat Labs product packages unstable channel
│   │   └── main/
│   ├── bookworm-stable/    # Halos stable for Bookworm
│   │   └── main/
│   ├── bookworm-unstable/  # Halos unstable for Bookworm
│   │   └── main/
│   ├── trixie-stable/      # Halos stable for Trixie
│   │   └── main/
│   └── trixie-unstable/    # Halos unstable for Trixie
│       └── main/
├── hat-labs-apt-key.asc    # Public GPG key (ASCII armored)
├── hat-labs-apt-key.gpg    # Public GPG key (binary)
└── index.html              # Repository web interface
```

Each distribution directory contains:
- `Packages` - Package metadata file
- `Packages.gz` - Compressed package metadata
- `Release` - Distribution metadata and checksums
- `Release.gpg` - Detached signature
- `InRelease` - Inline-signed release file

### GitHub Actions Workflow

The core automation is implemented in `.github/workflows/update-repo.yml` which handles:

1. **Package Discovery** - Finds all Hat Labs repositories tagged with `apt-package` topic
2. **Package Download** - Downloads .deb artifacts from GitHub releases
   - Stable channel: Downloads from latest stable release
   - Unstable channel: Downloads from latest pre-release
3. **Repository Generation** - Creates APT repository metadata for each distribution
4. **Signing** - Cryptographically signs all Release files
5. **Deployment** - Publishes to GitHub Pages at apt.hatlabs.fi

### Package Source Repositories

Package repositories (e.g., HALPI2 firmware, cockpit-apt, halos-marine-containers) are responsible for:

1. **Building Packages** - Creating .deb files with proper metadata
2. **Publishing Artifacts** - Attaching .deb files to GitHub releases
3. **Triggering Updates** - Sending repository_dispatch events to apt.hatlabs.fi
4. **Build Isolation** - Using appropriate build environments for target distributions

## Data Flow

### Stable Channel Flow

```
Developer creates GitHub release
    ↓
Package repo workflow triggers
    ↓
Build .deb in distribution-specific container
    ↓
Attach .deb to GitHub release
    ↓
Send repository_dispatch to apt.hatlabs.fi
    payload: {distro: "trixie", channel: "stable", component: "main"}
    ↓
apt.hatlabs.fi workflow triggers
    ↓
Download .deb from release
    ↓
Add to pool/main/
    ↓
Generate Packages file for trixie-stable/main
    ↓
Generate and sign Release file
    ↓
Deploy to GitHub Pages
    ↓
Users run `apt update` and receive new package
```

### Unstable Channel Flow

```
Developer merges PR to main
    ↓
Package repo workflow triggers
    ↓
Build .deb in distribution-specific container
    ↓
Create or update pre-release with version tag (e.g., v0.2.0)
    ↓
Attach .deb to pre-release
    ↓
Send repository_dispatch to apt.hatlabs.fi
    payload: {distro: "bookworm", channel: "unstable", component: "main"}
    ↓
apt.hatlabs.fi workflow triggers
    ↓
Download .deb from latest pre-release
    ↓
Add to pool/main/ (replacing previous version)
    ↓
Generate Packages file for bookworm-unstable/main
    ↓
Generate and sign Release file
    ↓
Deploy to GitHub Pages
    ↓
Users run `apt update` and receive updated package
```

**Note**: The unstable channel downloads from the latest pre-release (by date), not from a special "unstable" tag. Package repositories create pre-releases with version tags (e.g., v0.2.0) marked with GitHub's pre-release checkbox.

## Workflow Dispatch Payload Handling

### Payload Structure

```json
{
  "event_type": "package-updated",
  "client_payload": {
    "repository": "hatlabs/cockpit-apt",
    "package_name": "cockpit-apt",
    "version": "1.2.3",
    "distro": "trixie",
    "channel": "stable",
    "component": "main"
  }
}
```

### Distribution Name Mapping

The workflow maps payload fields to APT distribution names:

```python
if payload.distro == "any":
    distribution = payload.channel  # "stable" or "unstable"
else:
    distribution = f"{payload.distro}-{payload.channel}"  # "bookworm-stable", etc.
```

This mapping allows:
- Hat Labs product packages to use simple "stable" and "unstable" distributions
- Halos packages to use explicit "bookworm-stable", "trixie-unstable", etc.

### Multiple Distribution Support

The workflow must support packages being added to multiple distributions simultaneously. This is particularly relevant for:
- Hat Labs product packages that could potentially be added to both "stable" and "unstable"
- Future scenarios where a single build might target multiple distributions

The payload may include either a single distribution or a list of distribution specifications.

## Repository Update Process

### Discovery Phase

The workflow uses GitHub's search API to find all repositories with the `apt-package` topic in the Hat Labs organization. This automatic discovery means:
- No manual configuration needed when adding new package repositories
- All package repos are treated uniformly
- The topic serves as the source of truth for what should be in the repository

### Download Phase

For each discovered repository:
1. Query GitHub API for latest release information
2. Filter for .deb assets
3. Download each .deb file
4. Extract and verify package metadata (Package, Version, Architecture)
5. Rename files to canonical Debian naming: `{package}_{version}_{arch}.deb`

### Build Phase

For each distribution:
1. Create directory structure: `dists/{distribution}/{component}/binary-{arch}/`
2. Copy all relevant packages to `pool/{component}/`
3. Run `dpkg-scanpackages` to generate Packages files for each architecture
4. Compress Packages files with gzip
5. Generate Release file with distribution metadata
6. Run `apt-ftparchive release` to add package checksums
7. Sign Release file with GPG (both detached and inline signatures)

### Web Interface Generation Phase

After repository metadata is generated, the workflow creates an HTML interface:

1. Parse package metadata from all distribution Packages files
2. Extract package information (name, version, description, architecture)
3. Group packages by distribution
4. Generate navigation between distributions
5. Create distribution-specific installation instructions
6. Build responsive HTML page with:
   - Repository overview and purpose
   - Distribution browser with tabs or navigation
   - Package listings per distribution
   - Installation instructions per distribution
   - GPG key download links and fingerprint

The web interface provides a user-friendly way to discover and understand available packages without requiring command-line APT tools.

### Deployment Phase

The entire `apt-repo/` directory is deployed to GitHub Pages using the peaceiris/actions-gh-pages action. This provides:
- Atomic updates (entire directory is replaced)
- HTTPS serving via GitHub Pages
- Custom domain support (apt.hatlabs.fi via CNAME)
- No separate hosting infrastructure needed

## Technology Stack

### Core Technologies

- **GitHub Actions** - Workflow automation and CI/CD
- **GitHub Pages** - Static file hosting with HTTPS
- **GitHub API** - Package discovery and artifact downloads
- **GPG** - Cryptographic signing of repository metadata
- **Debian Package Tools** - dpkg-dev, apt-utils for repository generation

### Debian Tools Usage

- `dpkg-scanpackages` - Generates Packages metadata files from .deb files
- `apt-ftparchive release` - Generates Release files with checksums
- `dpkg-deb` - Extracts package metadata for verification
- `gpg` - Signs Release files and exports public keys

### GitHub Features

- **Repository Topics** - Discovery mechanism for package repositories
- **Releases** - Package artifact storage
- **Repository Dispatch** - Event-driven workflow triggering
- **GitHub Pages** - Static site hosting
- **Secrets** - Secure GPG key storage

## Integration Points

### Package Repository Integration

Package repositories must:

1. **Tag with apt-package topic** - Enables automatic discovery
2. **Publish .deb files to releases** - Both stable releases and unstable "release"
3. **Send repository_dispatch events** - Triggers repository updates
4. **Include payload metadata** - Specifies distro, channel, component

### User Integration

In most cases, APT sources are pre-configured in Halos images. However, users may need to manually add sources for specific use cases or when running on non-Halos systems.

End users interact through standard APT commands:

```bash
# Add repository GPG key
curl -fsSL https://apt.hatlabs.fi/hat-labs-apt-key.asc | \
  sudo gpg --dearmor -o /usr/share/keyrings/hatlabs.gpg

# Add APT source
echo "deb [signed-by=/usr/share/keyrings/hatlabs.gpg] https://apt.hatlabs.fi trixie-stable main" | \
  sudo tee /etc/apt/sources.list.d/hatlabs.list

# Update and install
sudo apt update
sudo apt install <package-name>
```

## Deployment Architecture

### Hosting Environment

- **Production**: GitHub Pages at apt.hatlabs.fi
- **HTTPS**: Provided automatically by GitHub Pages
- **DNS**: CNAME record pointing to GitHub Pages
- **Geographic Distribution**: GitHub's CDN infrastructure

### Update Frequency

- **On-demand**: Triggered by repository_dispatch from package repos
- **Daily**: Scheduled rebuild at 06:00 UTC (cron: '0 6 * * *')
- **Manual**: Can be triggered via workflow_dispatch

### Scalability Considerations

Current architecture scales well for Hat Labs' needs:
- GitHub Pages handles traffic distribution
- Repository metadata is lightweight and compresses well
- Package downloads are served directly from GitHub's infrastructure
- No database or stateful services required

Potential bottlenecks:
- GitHub Actions workflow concurrency limits
- GitHub Pages bandwidth (soft limits, rarely hit)
- Manual intervention needed for major structural changes

## Security Considerations

### Package Authenticity

All packages and repository metadata are cryptographically signed using GPG:
- Private key stored in GitHub Secrets (`APT_SIGNING_KEY`)
- Public key published at apt.hatlabs.fi/hat-labs-apt-key.asc
- Users verify signatures through APT's built-in mechanisms
- Tampering with packages or metadata is detectable

### Access Control

- **Repository Write Access**: Limited to Hat Labs organization members
- **GPG Private Key**: Stored in GitHub Secrets, accessible only to workflows
- **GitHub Pages**: Read-only public access, writes only via authorized workflows
- **Source Packages**: Each package repo controls its own build process

### Supply Chain Security

Package repositories are responsible for:
- Secure build environments (using trusted base images)
- Dependency verification during build
- Vulnerability scanning of built packages
- Proper version tracking and signing

The APT repository itself:
- Only downloads from official GitHub releases (authenticated API access)
- Verifies package metadata before publishing
- Maintains audit trail through git history
- Logs all workflow executions

### Vulnerability Response

When vulnerabilities are discovered:
1. Package maintainer creates patched version
2. New release triggers automatic repository update
3. Updated packages available to users within minutes
4. Users update via standard `apt upgrade` process

## Monitoring and Maintenance

### Health Indicators

- **Workflow Success Rate**: All update-repo.yml runs should succeed
- **Package Count**: Should match expected packages from all source repos
- **Signature Validity**: All Release files must have valid signatures
- **GitHub Pages Status**: Site should be accessible and serving correct content

### Maintenance Tasks

**Regular**:
- Monitor workflow execution for failures
- Review package discovery results to ensure all repos are found
- Verify GPG key expiration date

**Periodic**:
- Review and update supported distributions (add new, deprecate old)
- Audit package repository compliance with payload format
- Update documentation for new distribution additions

**As Needed**:
- Rotate GPG signing key (with user notification period)
- Adjust workflow for new GitHub features or Debian best practices
- Add support for new architectures or components

## Future Expansion

### Planned Enhancements

- **Multi-distribution web interface** - Browsing interface for all distributions with package discovery
- **Per-distribution package filtering** - Control which packages appear in which distributions
- **Multiple component support** - Separating packages into main/contrib/non-free
- **Automated testing** - Verify repository structure after updates

### Potential Additions

- **Package metrics** - Download statistics and usage tracking
- **Changelog aggregation** - Unified changelog across all packages
- **Version history** - Track package version changes over time
- **Automated announcements** - Notify users of new package versions
