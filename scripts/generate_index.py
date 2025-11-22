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

CSS_CONTENT = '''* { box-sizing: border-box; margin: 0; padding: 0; }
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
.dist-card h3 a {
    color: #2c5282;
    text-decoration: none;
}
.dist-card h3 a:hover {
    text-decoration: underline;
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

.breadcrumb {
    margin-bottom: 20px;
    font-size: 0.9em;
}
.breadcrumb a {
    color: #4299e1;
    text-decoration: none;
}
.breadcrumb a:hover {
    text-decoration: underline;
}

footer {
    margin-top: 60px;
    padding-top: 20px;
    border-top: 1px solid #e2e8f0;
    color: #718096;
    font-size: 0.9em;
}

/* Collapsible component sections */
.component-group {
    border: 1px solid #e2e8f0;
    border-radius: 6px;
    margin-bottom: 15px;
    background: white;
}
.component-group summary {
    padding: 12px 15px;
    cursor: pointer;
    font-weight: 600;
    color: #2c5282;
    background: #f7fafc;
    border-radius: 6px;
    list-style: none;
    display: flex;
    align-items: center;
    gap: 8px;
}
.component-group summary::-webkit-details-marker { display: none; }
.component-group summary::before {
    content: "▶";
    font-size: 0.7em;
    transition: transform 0.2s;
}
.component-group[open] summary::before {
    transform: rotate(90deg);
}
.component-group[open] summary {
    border-bottom: 1px solid #e2e8f0;
    border-radius: 6px 6px 0 0;
}
.component-group .component-content {
    padding: 15px;
}
.component-group .pkg-count {
    font-weight: normal;
    color: #718096;
    font-size: 0.9em;
}
.component-group .empty-msg {
    color: #718096;
    font-style: italic;
}

/* Collapsible install command section */
.install-section {
    margin-top: 20px;
    border: 1px solid #e2e8f0;
    border-radius: 6px;
    background: #f7fafc;
}
.install-section summary {
    padding: 10px 15px;
    cursor: pointer;
    color: #4a5568;
    font-size: 0.9em;
    list-style: none;
    display: flex;
    align-items: center;
    gap: 6px;
}
.install-section summary::-webkit-details-marker { display: none; }
.install-section summary::before {
    content: "▶";
    font-size: 0.65em;
    transition: transform 0.2s;
}
.install-section[open] summary::before {
    transform: rotate(90deg);
}
.install-section[open] summary {
    border-bottom: 1px solid #e2e8f0;
}
.install-section .install-content {
    padding: 15px;
}
.install-section .command-block {
    margin: 0;
}

@media (max-width: 768px) {
    .container { padding: 20px; }
    h1 { font-size: 2em; }
    .command-block { font-size: 0.8em; }
}
'''


@dataclass
class Package:
    """Represents a Debian package."""
    name: str
    version: str
    description: str
    architecture: str
    filename: str
    component: str = 'main'
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

    @property
    def components(self) -> List[str]:
        """Return list of components that have packages, in preferred order."""
        found = set(p.component for p in self.packages)
        # Return in preferred order: main first, then hatlabs, then others
        ordered = []
        for comp in ['main', 'hatlabs']:
            if comp in found:
                ordered.append(comp)
                found.remove(comp)
        ordered.extend(sorted(found))
        return ordered if ordered else ['main']  # Always show at least main

    def packages_by_component(self, component: str) -> List[Package]:
        """Return packages for a specific component."""
        return [p for p in self.packages if p.component == component]

    def component_package_count(self, component: str) -> int:
        """Return number of unique packages in a component."""
        return len(set(p.name for p in self.packages if p.component == component))


def parse_packages_file(packages_file: Path, component: str = 'main') -> List[Package]:
    """Parse a Debian Packages file and extract package information.

    Args:
        packages_file: Path to the Packages file
        component: Component name (main, hatlabs, etc.) for tracking
    """
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
                                filename=current_package['Filename'],
                                component=component
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
                    filename=current_package['Filename'],
                    component=component
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
    """Scan repository for all distributions and their packages.

    Scans all components (main, hatlabs, etc.) found in each distribution.
    """
    distributions = []
    dists_dir = repo_dir / 'dists'

    if not dists_dir.exists():
        return distributions

    # Known components in preferred order
    known_components = ['main', 'hatlabs']

    for dist_path in sorted(dists_dir.iterdir()):
        if not dist_path.is_dir():
            continue

        dist_name = dist_path.name
        display_name, description = get_distribution_info(dist_name)

        # Discover all components in this distribution
        components = []
        for item in dist_path.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                # Check if it looks like a component (has binary-* subdirs)
                if any((item / f'binary-{arch}').exists() for arch in SUPPORTED_ARCHITECTURES):
                    components.append(item.name)

        # Sort components: known ones first in order, then others alphabetically
        def component_sort_key(c):
            try:
                return (0, known_components.index(c))
            except ValueError:
                return (1, c)
        components.sort(key=component_sort_key)

        # Collect packages from all components and architectures
        all_packages = []
        for component in components:
            for arch in SUPPORTED_ARCHITECTURES:
                packages_file = dist_path / component / f'binary-{arch}' / 'Packages'
                if packages_file.exists():
                    all_packages.extend(parse_packages_file(packages_file, component))

        # Deduplicate packages while tracking all architectures.
        # Use (name, component) as key since same package name could be in different components.
        # Packages can legitimately appear in multiple architecture directories
        # (e.g., both binary-arm64 and binary-all).
        unique_packages = {}
        for pkg in all_packages:
            key = (pkg.name, pkg.component)
            if key not in unique_packages:
                unique_packages[key] = pkg
            else:
                # Package already exists - check version and merge architectures
                existing = unique_packages[key]
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
            packages=sorted(unique_packages.values(), key=lambda p: (p.component, p.name))
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


def get_component_display_name(component: str) -> str:
    """Get a human-readable display name for a component."""
    names = {
        'main': 'Main Packages',
        'hatlabs': 'Hat Labs Products',
    }
    return names.get(component, component.title())


def render_distribution_summary_card(dist: Distribution) -> str:
    """Render HTML for a distribution summary card (for main index).

    Summary cards show distribution info and package count but no individual packages.
    They include a link to the distribution's dedicated page.
    """
    parts = []

    parts.append(f'\n            <div class="dist-card">')
    parts.append(f'\n                <h3><a href="{html.escape(dist.name)}.html">{html.escape(dist.display_name)}</a></h3>')
    parts.append(f'\n                <p class="dist-meta">{dist.package_count} packages</p>')
    parts.append(f'\n                <p class="dist-desc">{html.escape(dist.description)}</p>')

    # Add unstable warning if applicable
    if 'unstable' in dist.name:
        parts.append(UNSTABLE_WARNING)

    # Link to distribution page
    parts.append(f'\n                <p style="margin-top: 15px;"><a href="{html.escape(dist.name)}.html" style="color: #4299e1; text-decoration: none;">View all {dist.package_count} packages →</a></p>')

    # Add collapsible installation command section
    components_str = ' '.join(dist.components)
    parts.append('\n                <details class="install-section">')
    parts.append('\n                    <summary>Add this distribution</summary>')
    parts.append('\n                    <div class="install-content">')
    parts.append(f'\n                        <div class="command-block">echo "deb [signed-by={html.escape(KEYRING_PATH)}] {html.escape(REPO_URL)} {html.escape(dist.name)} {html.escape(components_str)}" | sudo tee -a /etc/apt/sources.list.d/hatlabs.list</div>')
    parts.append('\n                    </div>')
    parts.append('\n                </details>')

    parts.append('\n            </div>')

    return ''.join(parts)


def render_package_item(pkg: Package) -> str:
    """Render HTML for a single package item."""
    parts = []
    parts.append(f'\n                        <div class="package-item">')
    # Display all architectures if multiple, otherwise just the primary
    arch_badges = ' '.join(f'<span class="arch-badge">{html.escape(arch)}</span>'
                           for arch in pkg.all_architectures)
    parts.append(f'\n                            <h4>{html.escape(pkg.name)} <span class="version">v{html.escape(pkg.version)}</span> {arch_badges}</h4>')
    parts.append(f'\n                            <p class="description">{html.escape(pkg.description)}</p>')
    parts.append(f'\n                            <div class="install-cmd">sudo apt install {html.escape(pkg.name)}</div>')
    parts.append('\n                        </div>')
    return ''.join(parts)


def render_component_group(dist: Distribution, component: str, expanded: bool = True) -> str:
    """Render HTML for a collapsible component group with its packages."""
    parts = []
    packages = dist.packages_by_component(component)
    pkg_count = len(packages)
    display_name = get_component_display_name(component)

    open_attr = ' open' if expanded else ''
    parts.append(f'\n                    <details class="component-group"{open_attr}>')
    parts.append(f'\n                        <summary>{html.escape(display_name)} <span class="pkg-count">({pkg_count} packages)</span></summary>')
    parts.append('\n                        <div class="component-content">')

    if packages:
        for pkg in packages:
            parts.append(render_package_item(pkg))
    else:
        parts.append('\n                            <p class="empty-msg">No packages in this component yet.</p>')

    parts.append('\n                        </div>')
    parts.append('\n                    </details>')

    return ''.join(parts)


def render_distribution_card(dist: Distribution) -> str:
    """Render HTML for a single distribution card (full version with all packages).

    Packages are organized into collapsible groups by component.
    """
    parts = []

    parts.append(f'\n            <div class="dist-card">')
    parts.append(f'\n                <h3>{html.escape(dist.display_name)}</h3>')
    parts.append(f'\n                <p class="dist-meta">{dist.package_count} packages</p>')
    parts.append(f'\n                <p class="dist-desc">{html.escape(dist.description)}</p>')

    # Add unstable warning if applicable
    if 'unstable' in dist.name:
        parts.append(UNSTABLE_WARNING)

    # Render package list grouped by component
    parts.append('\n                <div class="package-list">')
    parts.append('\n                    <strong>Available Packages:</strong>')

    for i, component in enumerate(dist.components):
        # Expand the first component that has packages, or the first one if all empty
        has_packages = dist.component_package_count(component) > 0
        expanded = has_packages or i == 0
        parts.append(render_component_group(dist, component, expanded=expanded))

    parts.append('\n                </div>')

    # Add collapsible installation command section (after packages)
    components_str = ' '.join(dist.components)
    parts.append('\n                <details class="install-section">')
    parts.append('\n                    <summary>Add this distribution</summary>')
    parts.append('\n                    <div class="install-content">')
    parts.append(f'\n                        <div class="command-block">echo "deb [signed-by={html.escape(KEYRING_PATH)}] {html.escape(REPO_URL)} {html.escape(dist.name)} {html.escape(components_str)}" | sudo tee -a /etc/apt/sources.list.d/hatlabs.list</div>')
    parts.append('\n                    </div>')
    parts.append('\n                </details>')

    parts.append('\n            </div>')

    return ''.join(parts)


def get_html_header(breadcrumb: str = '') -> str:
    """Get HTML header with CSS link (shared stylesheet) and optional breadcrumb.

    Args:
        breadcrumb: Optional breadcrumb HTML to include before header

    Returns:
        HTML header with linked stylesheet
    """
    header = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Hat Labs APT Repository</title>
    <link rel="stylesheet" href="styles.css">
</head>
<body>
    <div class="container">'''

    if breadcrumb:
        header += f'\n        {breadcrumb}'

    header += '''
        <header>
            <h1><span class="emoji">🎩</span> Hat Labs APT Repository</h1>
            <p class="subtitle">Debian packages for Hat Labs products and Halos operating system</p>
        </header>
'''
    return header


def render_main_index(distributions: List[Distribution], gpg_fingerprint: str) -> str:
    """Generate the main index page with distribution summary cards.

    The main index shows repository setup instructions and summary cards for all
    distributions, but does not show individual package listings.
    """
    # Group distributions by type
    product_dists = [d for d in distributions if is_product_distribution(d.name)]
    halos_dists = [d for d in distributions if not is_product_distribution(d.name)]

    html_parts = []

    # HTML header with stylesheet link
    html_parts.append(get_html_header())

    # Installation instructions
    html_parts.append(f'''
        <div class="info-box">
            <h3>🔐 Repository Setup</h3>
            <p>Add the Hat Labs repository to your system:</p>
            <div class="command-block">curl -fsSL {html.escape(REPO_URL)}/hat-labs-apt-key.asc | sudo gpg --dearmor -o {html.escape(KEYRING_PATH)}
echo "deb [signed-by={html.escape(KEYRING_PATH)}] {html.escape(REPO_URL)} <distribution> <components>" | sudo tee -a /etc/apt/sources.list.d/hatlabs.list
sudo apt update</div>
            <p style="margin-top: 10px;"><small>Replace <code>&lt;distribution&gt;</code> with your desired distribution and <code>&lt;components&gt;</code> with available components (e.g., <code>main hatlabs</code>)</small></p>
        </div>
''')

    # Hat Labs Product Distributions
    if product_dists:
        html_parts.append('\n        <div class="dist-section">')
        html_parts.append('\n            <h2>📦 Hat Labs Product Packages</h2>')
        html_parts.append('\n            <p style="margin-bottom: 20px; color: #4a5568;">Firmware and drivers for Hat Labs hardware products (HALPI2, etc.)</p>')

        for dist in product_dists:
            html_parts.append(render_distribution_summary_card(dist))

        html_parts.append('\n        </div>')

    # Halos Distributions
    if halos_dists:
        html_parts.append('\n        <div class="dist-section">')
        html_parts.append('\n            <h2>🌊 Halos Operating System Packages</h2>')
        html_parts.append('\n            <p style="margin-bottom: 20px; color: #4a5568;">Halos-specific packages for different Debian/Raspberry Pi OS releases</p>')

        for dist in halos_dists:
            html_parts.append(render_distribution_summary_card(dist))

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


def render_distribution_page(dist: Distribution, gpg_fingerprint: str) -> str:
    """Generate a dedicated page for a single distribution with all packages.

    Each distribution gets its own page showing only packages for that distribution,
    with a breadcrumb link back to the main index.
    """
    html_parts = []

    # Breadcrumb navigation
    breadcrumb = '<div class="breadcrumb"><a href="index.html">← Back to all distributions</a></div>'

    # HTML header with stylesheet link and breadcrumb
    html_parts.append(get_html_header(breadcrumb))

    # Distribution card with all details
    html_parts.append('\n        <div class="dist-section">')
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
            <p><a href="index.html">← Back to all distributions</a></p>
            <p>🔒 This repository is cryptographically signed for security</p>
        </footer>
    </div>
</body>
</html>
''')

    return ''.join(html_parts)


def generate_html(distributions: List[Distribution], gpg_fingerprint: str) -> str:
    """Generate the complete HTML index page (legacy single-page version).

    This function is kept for backward compatibility. The main workflow now uses
    render_main_index() and render_distribution_page() for multi-page generation.
    """

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
echo "deb [signed-by={html.escape(KEYRING_PATH)}] {html.escape(REPO_URL)} <distribution> <components>" | sudo tee -a /etc/apt/sources.list.d/hatlabs.list
sudo apt update</div>
            <p style="margin-top: 10px;"><small>Replace <code>&lt;distribution&gt;</code> with your desired distribution and <code>&lt;components&gt;</code> with available components (e.g., <code>main hatlabs</code>)</small></p>
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


def write_shared_css(output_dir: Path) -> None:
    """Write shared CSS file to output directory for all pages.

    This enables browser caching and reduces page sizes by not duplicating
    CSS in every HTML file.
    """
    css_file = output_dir / 'styles.css'
    try:
        css_file.write_text(CSS_CONTENT, encoding='utf-8')
        print(f"✓ Generated {css_file}")
    except OSError as e:
        print(f"Error: Failed to write CSS file: {e}", file=sys.stderr)
        raise


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Generate APT repository index pages')
    parser.add_argument('repo_dir', type=Path, help='Path to apt-repo directory')
    parser.add_argument('--gpg-fingerprint', required=True, help='GPG key fingerprint')
    parser.add_argument('--output-dir', type=Path, help='Output directory (default: repo_dir)')
    parser.add_argument('--legacy', action='store_true', help='Generate legacy single-page layout (default: multi-page)')

    args = parser.parse_args()

    if not args.repo_dir.exists():
        print(f"Error: Repository directory {args.repo_dir} does not exist", file=sys.stderr)
        return 1

    output_dir = args.output_dir or args.repo_dir

    # Scan distributions
    print(f"Scanning distributions in {args.repo_dir}...")
    distributions = scan_distributions(args.repo_dir)

    if not distributions:
        print("Warning: No distributions found", file=sys.stderr)
    else:
        for dist in distributions:
            print(f"  - {dist.name}: {dist.package_count} packages")

    # Generate HTML files
    print("Generating HTML pages...")

    try:
        if args.legacy:
            # Legacy: generate single-page layout
            html_content = generate_html(distributions, args.gpg_fingerprint)
            output_file = output_dir / 'index.html'
            output_file.write_text(html_content, encoding='utf-8')
            print(f"✓ Generated {output_file}")
        else:
            # Multi-page: generate main index + distribution pages

            # Write shared CSS file (used by all pages)
            write_shared_css(output_dir)

            # Generate main index
            main_html = render_main_index(distributions, args.gpg_fingerprint)
            index_file = output_dir / 'index.html'
            index_file.write_text(main_html, encoding='utf-8')
            print(f"✓ Generated {index_file}")

            # Generate distribution pages
            for dist in distributions:
                dist_html = render_distribution_page(dist, args.gpg_fingerprint)
                dist_file = output_dir / f'{dist.name}.html'
                dist_file.write_text(dist_html, encoding='utf-8')
                print(f"✓ Generated {dist_file}")

    except OSError as e:
        print(f"Error: Failed to write HTML files: {e}", file=sys.stderr)
        return 2

    return 0


if __name__ == '__main__':
    sys.exit(main())
