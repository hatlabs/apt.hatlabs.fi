#!/usr/bin/env python3
"""
Generate multi-distribution APT repository index page.

This script parses Packages files from all distributions and generates
an HTML page with distribution navigation and package listings.
"""

import argparse
import sys
from pathlib import Path
from typing import List, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timezone
import html


# Constants
REPO_URL = 'https://apt.hatlabs.fi'
KEYRING_PATH = '/usr/share/keyrings/hatlabs.gpg'
SUPPORTED_ARCHITECTURES = ['arm64', 'armhf', 'all']

UNSTABLE_WARNING = '''
                <div class="warning-box">
                    <strong>⚠️ Unstable Channel:</strong> Contains latest packages from main branch. May include untested changes. Use stable for production systems.
                </div>
'''


@dataclass
class Package:
    """Represents a Debian package."""
    name: str
    version: str
    description: str
    architecture: str
    filename: str
    all_architectures: List[str] = field(default_factory=list)

    def __post_init__(self):
        """Initialize all_architectures if not provided."""
        if not self.all_architectures:
            self.all_architectures = [self.architecture]


@dataclass
class Distribution:
    """Represents an APT distribution."""
    name: str
    display_name: str
    description: str
    packages: List[Package]

    @property
    def package_count(self) -> int:
        """Return number of unique packages."""
        return len(set(p.name for p in self.packages))


def parse_packages_file(packages_file: Path) -> List[Package]:
    """Parse a Debian Packages file and extract package information."""
    packages = []
    current_package = {}
    last_key = None

    try:
        with open(packages_file, 'r', encoding='utf-8', errors='replace') as f:
            for line in f:
                line = line.rstrip()

                if not line:
                    # Empty line marks end of package entry
                    if current_package:
                        # Only add if we have all required fields
                        if all(k in current_package for k in ['Package', 'Version', 'Description', 'Filename']):
                            packages.append(Package(
                                name=current_package['Package'],
                                version=current_package['Version'],
                                description=current_package['Description'],
                                architecture=current_package.get('Architecture', 'unknown'),
                                filename=current_package['Filename']
                            ))
                        current_package = {}
                        last_key = None
                elif line.startswith((' ', '\t')) and last_key:
                    # Continuation line - append to previous field
                    current_package[last_key] += ' ' + line.strip()
                elif ':' in line:
                    key, _, value = line.partition(':')
                    key = key.strip()
                    current_package[key] = value.strip()
                    last_key = key

            # Handle last package if file doesn't end with blank line
            if current_package and all(k in current_package for k in ['Package', 'Version', 'Description', 'Filename']):
                packages.append(Package(
                    name=current_package['Package'],
                    version=current_package['Version'],
                    description=current_package['Description'],
                    architecture=current_package.get('Architecture', 'unknown'),
                    filename=current_package['Filename']
                ))
    except FileNotFoundError:
        # Distribution directory exists but no packages yet
        pass

    return packages


def get_distribution_info(dist_name: str) -> Tuple[str, str]:
    """Get display name and description for a distribution.

    Returns a tuple of (display_name, description) for known distributions.
    For unknown distributions, returns a title-cased name and generic description.

    Note: When adding new distributions to the repository, update this function
    to provide proper display names and descriptions.
    """
    distributions = {
        'stable': ('Stable', 'Hat Labs product packages (stable releases)'),
        'unstable': ('Unstable', 'Hat Labs product packages (rolling, latest from main)'),
        'bookworm-stable': ('Bookworm Stable', 'Halos packages for Debian Bookworm (stable releases)'),
        'bookworm-unstable': ('Bookworm Unstable', 'Halos packages for Debian Bookworm (rolling)'),
        'trixie-stable': ('Trixie Stable', 'Halos packages for Debian Trixie (stable releases)'),
        'trixie-unstable': ('Trixie Unstable', 'Halos packages for Debian Trixie (rolling)'),
    }
    return distributions.get(dist_name, (dist_name.title(), f'{dist_name} distribution'))


def scan_distributions(repo_dir: Path) -> List[Distribution]:
    """Scan repository for all distributions and their packages."""
    distributions = []
    dists_dir = repo_dir / 'dists'

    if not dists_dir.exists():
        return distributions

    for dist_path in sorted(dists_dir.iterdir()):
        if not dist_path.is_dir():
            continue

        dist_name = dist_path.name
        display_name, description = get_distribution_info(dist_name)

        # Collect packages from all architectures
        all_packages = []
        for arch in SUPPORTED_ARCHITECTURES:
            packages_file = dist_path / 'main' / f'binary-{arch}' / 'Packages'
            if packages_file.exists():
                all_packages.extend(parse_packages_file(packages_file))

        # Deduplicate packages while tracking all architectures.
        # Packages can legitimately appear in multiple architecture directories
        # (e.g., both binary-arm64 and binary-all).
        unique_packages = {}
        for pkg in all_packages:
            if pkg.name not in unique_packages:
                unique_packages[pkg.name] = pkg
            else:
                # Package already exists - check version and merge architectures
                existing = unique_packages[pkg.name]
                if pkg.version != existing.version:
                    print(f"Warning: Package {pkg.name} has different versions across architectures: "
                          f"{existing.architecture}={existing.version}, {pkg.architecture}={pkg.version}",
                          file=sys.stderr)
                if pkg.architecture not in existing.all_architectures:
                    existing.all_architectures.append(pkg.architecture)
                    existing.all_architectures.sort()  # Ensure consistent ordering
                # Update primary architecture display to preferred one
                existing.architecture = get_preferred_architecture(existing.architecture, pkg.architecture)

        distributions.append(Distribution(
            name=dist_name,
            display_name=display_name,
            description=description,
            packages=sorted(unique_packages.values(), key=lambda p: p.name)
        ))

    return distributions


def get_preferred_architecture(arch1: str, arch2: str) -> str:
    """Return the preferred architecture for display purposes.

    Prefers more specific architectures (arm64, armhf) over generic ones (all).
    arm64 is preferred over armhf for display purposes.
    """
    # Define preference order (higher index = higher priority)
    preference = {'all': 0, 'armhf': 1, 'arm64': 2}

    pref1 = preference.get(arch1, 1)  # Default to middle priority
    pref2 = preference.get(arch2, 1)

    return arch1 if pref1 >= pref2 else arch2


def is_product_distribution(dist_name: str) -> bool:
    """Return True if the distribution is a Hat Labs product distribution.

    Product distributions don't contain a hyphen (e.g., 'stable', 'unstable').
    Halos distributions are named with pattern '{distro}-{channel}' (e.g., 'bookworm-stable').
    """
    return '-' not in dist_name


def render_distribution_card(dist: Distribution) -> str:
    """Render HTML for a single distribution card."""
    parts = []

    parts.append(f'\n            <div class="dist-card">')
    parts.append(f'\n                <h3>{html.escape(dist.display_name)}</h3>')
    parts.append(f'\n                <p class="dist-meta">{dist.package_count} packages</p>')
    parts.append(f'\n                <p class="dist-desc">{html.escape(dist.description)}</p>')

    # Add unstable warning if applicable
    if 'unstable' in dist.name:
        parts.append(UNSTABLE_WARNING)

    # Add installation command
    parts.append(f'\n                <strong>Add this distribution:</strong>')
    parts.append(f'\n                <div class="command-block">echo "deb [signed-by={html.escape(KEYRING_PATH)}] {html.escape(REPO_URL)} {html.escape(dist.name)} main" | sudo tee -a /etc/apt/sources.list.d/hatlabs.list</div>')

    # Render package list
    if dist.packages:
        parts.append('\n                <div class="package-list">')
        parts.append('\n                    <strong>Available Packages:</strong>')
        for pkg in dist.packages:
            parts.append(f'\n                    <div class="package-item">')
            # Display all architectures if multiple, otherwise just the primary
            arch_badges = ' '.join(f'<span class="arch-badge">{html.escape(arch)}</span>'
                                   for arch in pkg.all_architectures)
            parts.append(f'\n                        <h4>{html.escape(pkg.name)} <span class="version">v{html.escape(pkg.version)}</span> {arch_badges}</h4>')
            parts.append(f'\n                        <p class="description">{html.escape(pkg.description)}</p>')
            parts.append(f'\n                        <div class="install-cmd">sudo apt install {html.escape(pkg.name)}</div>')
            parts.append('\n                    </div>')
        parts.append('\n                </div>')
    else:
        parts.append('\n                <p style="color: #718096; font-style: italic;">No packages available yet.</p>')

    parts.append('\n            </div>')

    return ''.join(parts)


def generate_html(distributions: List[Distribution], gpg_fingerprint: str) -> str:
    """Generate the complete HTML index page."""

    # Group distributions by type
    product_dists = [d for d in distributions if is_product_distribution(d.name)]
    halos_dists = [d for d in distributions if not is_product_distribution(d.name)]

    html_parts = []

    # HTML header
    html_parts.append('''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Hat Labs APT Repository</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            line-height: 1.6;
            color: #2d3748;
            background: #f7fafc;
            padding: 20px;
        }
        .container { max-width: 1200px; margin: 0 auto; background: white; padding: 40px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
        header { margin-bottom: 40px; border-bottom: 3px solid #4299e1; padding-bottom: 20px; }
        h1 { color: #2d3748; font-size: 2.5em; margin-bottom: 10px; }
        h1 .emoji { font-style: normal; }
        .subtitle { color: #718096; font-size: 1.1em; }

        .info-box {
            background: #ebf8ff;
            border-left: 4px solid #4299e1;
            padding: 20px;
            margin: 30px 0;
            border-radius: 4px;
        }
        .info-box h3 { color: #2c5282; margin-bottom: 10px; }

        .warning-box {
            background: #fef5e7;
            border-left: 4px solid #f39c12;
            padding: 15px;
            margin: 20px 0;
            border-radius: 4px;
        }

        .dist-section { margin: 40px 0; }
        .dist-section h2 {
            color: #2d3748;
            border-bottom: 2px solid #e2e8f0;
            padding-bottom: 10px;
            margin-bottom: 20px;
        }

        .dist-card {
            background: #f7fafc;
            border: 1px solid #e2e8f0;
            border-radius: 6px;
            padding: 25px;
            margin-bottom: 30px;
        }
        .dist-card h3 {
            color: #2c5282;
            font-size: 1.5em;
            margin-bottom: 10px;
        }
        .dist-meta {
            color: #718096;
            font-size: 0.95em;
            margin-bottom: 20px;
        }
        .dist-desc {
            margin-bottom: 20px;
            color: #4a5568;
        }

        .command-block {
            background: #2d3748;
            color: #e2e8f0;
            padding: 15px;
            border-radius: 6px;
            margin: 15px 0;
            font-family: "Monaco", "Courier New", monospace;
            font-size: 0.9em;
            overflow-x: auto;
            white-space: pre;
        }

        .package-list { margin-top: 25px; }
        .package-item {
            background: white;
            border: 1px solid #e2e8f0;
            border-radius: 4px;
            padding: 15px;
            margin-bottom: 12px;
        }
        .package-item h4 {
            color: #2d3748;
            margin-bottom: 5px;
        }
        .package-item .version {
            color: #718096;
            font-size: 0.9em;
            font-family: monospace;
        }
        .package-item .arch-badge {
            display: inline-block;
            background: #4299e1;
            color: white;
            padding: 2px 8px;
            border-radius: 3px;
            font-size: 0.8em;
            margin-left: 8px;
        }
        .package-item .description {
            color: #4a5568;
            margin-top: 8px;
            font-size: 0.95em;
        }

        .install-cmd {
            background: #f7fafc;
            border: 1px solid #e2e8f0;
            padding: 8px 12px;
            border-radius: 4px;
            margin-top: 10px;
            font-family: monospace;
            font-size: 0.9em;
        }

        footer {
            margin-top: 60px;
            padding-top: 20px;
            border-top: 1px solid #e2e8f0;
            color: #718096;
            font-size: 0.9em;
        }

        @media (max-width: 768px) {
            .container { padding: 20px; }
            h1 { font-size: 2em; }
            .command-block { font-size: 0.8em; }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1><span class="emoji">🎩</span> Hat Labs APT Repository</h1>
            <p class="subtitle">Debian packages for Hat Labs products and Halos operating system</p>
        </header>
''')

    # Installation instructions
    html_parts.append(f'''
        <div class="info-box">
            <h3>🔐 Repository Setup</h3>
            <p>Add the Hat Labs repository to your system:</p>
            <div class="command-block">curl -fsSL {html.escape(REPO_URL)}/hat-labs-apt-key.asc | sudo gpg --dearmor -o {html.escape(KEYRING_PATH)}
echo "deb [signed-by={html.escape(KEYRING_PATH)}] {html.escape(REPO_URL)} <distribution> main" | sudo tee -a /etc/apt/sources.list.d/hatlabs.list
sudo apt update</div>
            <p style="margin-top: 10px;"><small>Replace <code>&lt;distribution&gt;</code> with your desired distribution (see below)</small></p>
        </div>
''')

    # Hat Labs Product Distributions
    if product_dists:
        html_parts.append('\n        <div class="dist-section">')
        html_parts.append('\n            <h2>📦 Hat Labs Product Packages</h2>')
        html_parts.append('\n            <p style="margin-bottom: 20px; color: #4a5568;">Firmware and drivers for Hat Labs hardware products (HALPI2, etc.)</p>')

        for dist in product_dists:
            html_parts.append(render_distribution_card(dist))

        html_parts.append('\n        </div>')

    # Halos Distributions
    if halos_dists:
        html_parts.append('\n        <div class="dist-section">')
        html_parts.append('\n            <h2>🌊 Halos Operating System Packages</h2>')
        html_parts.append('\n            <p style="margin-bottom: 20px; color: #4a5568;">Halos-specific packages for different Debian/Raspberry Pi OS releases</p>')

        for dist in halos_dists:
            html_parts.append(render_distribution_card(dist))

        html_parts.append('\n        </div>')

    # GPG Key section
    html_parts.append(f'''
        <div class="info-box">
            <h3>🔑 Repository Signing Key</h3>
            <p>All packages are cryptographically signed for security.</p>
            <p style="margin-top: 10px;">
                Download: <a href="hat-labs-apt-key.asc">hat-labs-apt-key.asc</a><br>
                Fingerprint: <code>{html.escape(gpg_fingerprint)}</code>
            </p>
        </div>
''')

    # Footer
    current_time = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
    html_parts.append(f'''
        <footer>
            <p>Last updated: {current_time}</p>
            <p>Repository URL: <code>{html.escape(REPO_URL)}</code></p>
            <p>🔒 This repository is cryptographically signed for security</p>
        </footer>
    </div>
</body>
</html>
''')

    return ''.join(html_parts)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Generate APT repository index page')
    parser.add_argument('repo_dir', type=Path, help='Path to apt-repo directory')
    parser.add_argument('--gpg-fingerprint', required=True, help='GPG key fingerprint')
    parser.add_argument('--output', type=Path, help='Output HTML file (default: repo_dir/index.html)')

    args = parser.parse_args()

    if not args.repo_dir.exists():
        print(f"Error: Repository directory {args.repo_dir} does not exist", file=sys.stderr)
        return 1

    # Scan distributions
    print(f"Scanning distributions in {args.repo_dir}...")
    distributions = scan_distributions(args.repo_dir)

    if not distributions:
        print("Warning: No distributions found", file=sys.stderr)
    else:
        for dist in distributions:
            print(f"  - {dist.name}: {dist.package_count} packages")

    # Generate HTML
    print("Generating HTML...")
    html_content = generate_html(distributions, args.gpg_fingerprint)

    # Write output
    output_file = args.output or (args.repo_dir / 'index.html')
    try:
        output_file.write_text(html_content, encoding='utf-8')
        print(f"✓ Generated {output_file}")
    except OSError as e:
        print(f"Error: Failed to write to {output_file}: {e}", file=sys.stderr)
        return 2

    return 0


if __name__ == '__main__':
    sys.exit(main())
