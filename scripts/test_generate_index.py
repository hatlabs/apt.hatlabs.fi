#!/usr/bin/env python3
"""
Test suite for generate-index.py multi-page generation.

Tests the new multi-page functionality that splits distributions into separate pages.
"""

import pytest
import tempfile
from pathlib import Path
from dataclasses import dataclass
from generate_index import (
    Package,
    Distribution,
    render_distribution_summary_card,
    render_main_index,
    render_distribution_page,
    render_component_group,
    scan_distributions,
    get_distribution_info,
    get_component_display_name,
)


@pytest.fixture
def sample_distribution():
    """Create a sample distribution with test data."""
    packages = [
        Package(
            name='test-pkg-1',
            version='1.0.0',
            description='First test package',
            architecture='arm64',
            filename='pool/test-pkg-1_1.0.0_arm64.deb',
            component='main',
            all_architectures=['arm64']
        ),
        Package(
            name='test-pkg-2',
            version='2.1.0',
            description='Second test package',
            architecture='all',
            filename='pool/test-pkg-2_2.1.0_all.deb',
            component='main',
            all_architectures=['all']
        ),
    ]

    return Distribution(
        name='trixie-stable',
        display_name='Trixie Stable',
        description='Halos packages for Debian Trixie (stable releases)',
        packages=packages
    )


@pytest.fixture
def empty_distribution():
    """Create a distribution with no packages."""
    return Distribution(
        name='bookworm-unstable',
        display_name='Bookworm Unstable',
        description='Halos packages for Debian Bookworm (rolling)',
        packages=[]
    )


@pytest.fixture
def all_distributions():
    """Create all 6 test distributions."""
    return [
        Distribution(
            name='stable',
            display_name='Stable',
            description='Hat Labs product packages (stable releases)',
            packages=[
                Package(
                    name='pkg-a',
                    version='1.0',
                    description='Package A',
                    architecture='all',
                    filename='pool/pkg-a_1.0_all.deb',
                    component='main',
                    all_architectures=['all']
                )
            ]
        ),
        Distribution(
            name='unstable',
            display_name='Unstable',
            description='Hat Labs product packages (rolling, latest from main)',
            packages=[
                Package(
                    name='pkg-b',
                    version='2.0',
                    description='Package B',
                    architecture='all',
                    filename='pool/pkg-b_2.0_all.deb',
                    component='main',
                    all_architectures=['all']
                )
            ]
        ),
        Distribution(
            name='bookworm-stable',
            display_name='Bookworm Stable',
            description='Halos packages for Debian Bookworm (stable releases)',
            packages=[]
        ),
        Distribution(
            name='bookworm-unstable',
            display_name='Bookworm Unstable',
            description='Halos packages for Debian Bookworm (rolling)',
            packages=[]
        ),
        Distribution(
            name='trixie-stable',
            display_name='Trixie Stable',
            description='Halos packages for Debian Trixie (stable releases)',
            packages=[]
        ),
        Distribution(
            name='trixie-unstable',
            display_name='Trixie Unstable',
            description='Halos packages for Debian Trixie (rolling)',
            packages=[]
        ),
    ]


class TestDistributionSummaryCard:
    """Tests for distribution summary card rendering (for main index)."""

    def test_summary_card_contains_distribution_name(self, sample_distribution):
        """Summary card should include distribution display name."""
        html = render_distribution_summary_card(sample_distribution)
        assert 'Trixie Stable' in html

    def test_summary_card_contains_package_count(self, sample_distribution):
        """Summary card should show number of packages."""
        html = render_distribution_summary_card(sample_distribution)
        assert '2 packages' in html

    def test_summary_card_contains_description(self, sample_distribution):
        """Summary card should include distribution description."""
        html = render_distribution_summary_card(sample_distribution)
        assert 'Halos packages for Debian Trixie' in html

    def test_summary_card_no_package_list(self, sample_distribution):
        """Summary card should NOT include individual package listings."""
        html = render_distribution_summary_card(sample_distribution)
        assert 'test-pkg-1' not in html
        assert 'test-pkg-2' not in html
        assert 'package-list' not in html

    def test_summary_card_contains_link_to_distribution_page(self, sample_distribution):
        """Summary card should link to the distribution's dedicated page."""
        html = render_distribution_summary_card(sample_distribution)
        # Should have a link to trixie-stable.html
        assert 'trixie-stable.html' in html or 'href' in html

    def test_summary_card_zero_packages(self, empty_distribution):
        """Summary card should handle distributions with no packages."""
        html = render_distribution_summary_card(empty_distribution)
        assert '0 packages' in html
        assert 'Bookworm Unstable' in html


class TestDistributionPage:
    """Tests for individual distribution page rendering."""

    def test_distribution_page_title(self, sample_distribution):
        """Distribution page should display distribution name."""
        html = render_distribution_page(sample_distribution, 'ABC123')
        assert 'Trixie Stable' in html

    def test_distribution_page_contains_packages(self, sample_distribution):
        """Distribution page should list all packages for that distribution."""
        html = render_distribution_page(sample_distribution, 'ABC123')
        assert 'test-pkg-1' in html
        assert 'test-pkg-2' in html

    def test_distribution_page_package_versions(self, sample_distribution):
        """Distribution page should show package versions."""
        html = render_distribution_page(sample_distribution, 'ABC123')
        assert '1.0.0' in html
        assert '2.1.0' in html

    def test_distribution_page_package_descriptions(self, sample_distribution):
        """Distribution page should show package descriptions."""
        html = render_distribution_page(sample_distribution, 'ABC123')
        assert 'First test package' in html
        assert 'Second test package' in html

    def test_distribution_page_has_breadcrumb(self, sample_distribution):
        """Distribution page should have navigation back to main index."""
        html = render_distribution_page(sample_distribution, 'ABC123')
        # Should contain a link back to main index
        assert 'index.html' in html or 'Back' in html or 'breadcrumb' in html.lower()

    def test_distribution_page_unstable_warning(self):
        """Unstable distribution pages should include warning."""
        dist = Distribution(
            name='trixie-unstable',
            display_name='Trixie Unstable',
            description='Test unstable',
            packages=[]
        )
        html = render_distribution_page(dist, 'ABC123')
        assert 'unstable' in html.lower() or 'warning' in html.lower()

    def test_distribution_page_no_unstable_warning_for_stable(self, sample_distribution):
        """Stable distributions should not have unstable warning."""
        html = render_distribution_page(sample_distribution, 'ABC123')
        # Should not have the unstable warning
        assert '⚠️ Unstable Channel' not in html

    def test_distribution_page_empty_packages(self, empty_distribution):
        """Distribution page should handle empty package list gracefully."""
        html = render_distribution_page(empty_distribution, 'ABC123')
        assert 'Bookworm Unstable' in html
        # Should show message about no packages
        assert 'No packages' in html or 'packages available' in html.lower()

    def test_distribution_page_setup_command(self, sample_distribution):
        """Distribution page should include setup command for that distribution."""
        html = render_distribution_page(sample_distribution, 'ABC123')
        # Should include the distribution name in apt sources command
        assert 'trixie-stable' in html

    def test_distribution_page_gpg_fingerprint(self, sample_distribution):
        """Distribution page should display GPG fingerprint."""
        html = render_distribution_page(sample_distribution, 'ABC123DEF456')
        assert 'ABC123DEF456' in html


class TestMainIndex:
    """Tests for main index page rendering."""

    def test_main_index_has_setup_instructions(self, all_distributions):
        """Main index should include repository setup instructions."""
        html = render_main_index(all_distributions, 'ABC123')
        assert 'Repository Setup' in html or 'setup' in html.lower()
        assert 'gpg' in html.lower() or 'GPG' in html

    def test_main_index_has_all_distribution_cards(self, all_distributions):
        """Main index should have summary cards for all 6 distributions."""
        html = render_main_index(all_distributions, 'ABC123')
        # Should have all distribution names
        assert 'Stable' in html
        assert 'Unstable' in html
        assert 'Bookworm Stable' in html
        assert 'Bookworm Unstable' in html
        assert 'Trixie Stable' in html
        assert 'Trixie Unstable' in html

    def test_main_index_no_individual_packages(self, all_distributions):
        """Main index should NOT list individual packages."""
        html = render_main_index(all_distributions, 'ABC123')
        # Package names should not be on main index
        assert 'pkg-a' not in html
        assert 'pkg-b' not in html

    def test_main_index_has_product_section(self, all_distributions):
        """Main index should have section for Hat Labs product packages."""
        html = render_main_index(all_distributions, 'ABC123')
        # Should mention product packages or hat labs
        assert 'Product' in html or 'Hat Labs' in html

    def test_main_index_has_halos_section(self, all_distributions):
        """Main index should have section for Halos OS packages."""
        html = render_main_index(all_distributions, 'ABC123')
        assert 'Halos' in html or 'Operating System' in html

    def test_main_index_links_to_distribution_pages(self, all_distributions):
        """Main index cards should link to individual distribution pages."""
        html = render_main_index(all_distributions, 'ABC123')
        # Should have links to distribution pages
        assert 'stable.html' in html
        assert 'unstable.html' in html
        assert 'bookworm-stable.html' in html
        assert 'bookworm-unstable.html' in html
        assert 'trixie-stable.html' in html
        assert 'trixie-unstable.html' in html

    def test_main_index_gpg_fingerprint(self, all_distributions):
        """Main index should display GPG fingerprint."""
        html = render_main_index(all_distributions, 'TEST12345')
        assert 'TEST12345' in html

    def test_main_index_responsive_design(self, all_distributions):
        """Main index should have responsive design via external stylesheet."""
        html = render_main_index(all_distributions, 'ABC123')
        # Should link to external stylesheet (CSS extracted to styles.css)
        assert '<link rel="stylesheet" href="styles.css">' in html
        # Should have viewport meta tag for responsive design
        assert 'viewport' in html


class TestMultiPageGeneration:
    """Integration tests for complete multi-page generation."""

    def test_functions_exist(self):
        """All required functions should exist and be callable."""
        # Test that new functions are defined
        assert callable(render_distribution_summary_card)
        assert callable(render_main_index)
        assert callable(render_distribution_page)

    def test_main_index_is_html(self, all_distributions):
        """Main index should be valid HTML."""
        html = render_main_index(all_distributions, 'ABC123')
        assert '<!DOCTYPE html>' in html
        assert '<html' in html
        assert '</html>' in html

    def test_distribution_page_is_html(self, sample_distribution):
        """Distribution pages should be valid HTML."""
        html = render_distribution_page(sample_distribution, 'ABC123')
        assert '<!DOCTYPE html>' in html
        assert '<html' in html
        assert '</html>' in html

    def test_summary_card_is_valid_html_fragment(self, sample_distribution):
        """Summary cards should be valid HTML (fragment)."""
        html = render_distribution_summary_card(sample_distribution)
        assert '<div' in html
        assert 'Trixie Stable' in html

    def test_different_distributions_create_different_pages(self):
        """Different distributions should generate different page content."""
        dist1 = Distribution('dist1', 'Dist 1', 'Description 1', [])
        dist2 = Distribution('dist2', 'Dist 2', 'Description 2', [])

        html1 = render_distribution_page(dist1, 'ABC123')
        html2 = render_distribution_page(dist2, 'ABC123')

        # Pages should differ based on distribution
        assert 'Dist 1' in html1
        assert 'Dist 2' in html2
        assert 'Dist 1' not in html2
        assert 'Dist 2' not in html1


class TestFullWorkflowIntegration:
    """Integration tests for complete workflow with main() function."""

    def test_main_generates_all_files(self, tmp_path):
        """Test that main() generates all expected HTML and CSS files."""
        import sys
        from pathlib import Path

        # Create mock apt-repo directory structure
        repo_dir = tmp_path / "apt-repo"
        dists_dir = repo_dir / "dists"
        dists_dir.mkdir(parents=True)

        # Create minimal distribution structure
        for dist in ['stable', 'unstable', 'bookworm-stable', 'bookworm-unstable', 'trixie-stable', 'trixie-unstable']:
            dist_path = dists_dir / dist / 'main' / 'binary-all'
            dist_path.mkdir(parents=True)
            # Create empty Packages file
            (dist_path / 'Packages').touch()

        # Mock sys.argv for argparse
        original_argv = sys.argv
        try:
            sys.argv = [
                'generate_index.py',
                str(repo_dir),
                '--gpg-fingerprint', 'TEST_FINGERPRINT_123'
            ]

            # Import and call main() function
            import generate_index
            result = generate_index.main()

            # Check return code
            assert result == 0, "main() should return 0 on success"

            # Verify all expected files were generated
            assert (repo_dir / 'index.html').exists(), "index.html should exist"
            assert (repo_dir / 'styles.css').exists(), "styles.css should exist"

            # Check distribution pages
            for dist in ['stable', 'unstable', 'bookworm-stable', 'bookworm-unstable', 'trixie-stable', 'trixie-unstable']:
                html_file = repo_dir / f'{dist}.html'
                assert html_file.exists(), f"{dist}.html should exist"

                # Verify each page has the CSS link
                html_content = html_file.read_text()
                assert 'styles.css' in html_content, f"{dist}.html should link to styles.css"
                assert 'href="styles.css"' in html_content, f"{dist}.html should have proper stylesheet link"

        finally:
            sys.argv = original_argv

    def test_css_file_has_required_styles(self, tmp_path):
        """Test that generated CSS file contains required styles."""
        import sys
        import generate_index

        repo_dir = tmp_path / "apt-repo"
        dists_dir = repo_dir / "dists"
        dists_dir.mkdir(parents=True)

        original_argv = sys.argv
        try:
            sys.argv = [
                'generate_index.py',
                str(repo_dir),
                '--gpg-fingerprint', 'TEST'
            ]

            generate_index.main()

            css_file = repo_dir / 'styles.css'
            css_content = css_file.read_text()

            # Check for critical style classes
            assert '.dist-card' in css_content, "CSS should have .dist-card style"
            assert '.breadcrumb' in css_content, "CSS should have .breadcrumb style"
            assert '.package-item' in css_content, "CSS should have .package-item style"
            assert '@media' in css_content, "CSS should have responsive design rules"

        finally:
            sys.argv = original_argv


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
