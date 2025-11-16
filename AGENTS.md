⚠️ **THESE RULES ONLY APPLY TO FILES IN /apt.hatlabs.fi/** ⚠️

# Hat Labs APT Repository - Development Guide

## 🎯 For Agentic Coding: Use the HaLOS Workspace

This repository should be used as part of the halos-distro workspace for AI-assisted development:

```bash
# Clone workspace and all repos
git clone https://github.com/hatlabs/halos-distro.git
cd halos-distro
./run repos:clone
```

See `halos-distro/docs/` for development workflows and guidance.

## About This Project

APT repository infrastructure for Hat Labs packages and tools.

**Local Instructions**: For environment-specific instructions and configurations, see @CLAUDE.local.md (not committed to version control).

## Git Workflow Policy

**Branch Workflow:** Never push to main directly - always use feature branches and PRs.

## Repository Structure

This repository maintains the Hat Labs APT repository at https://apt.hatlabs.fi.

- **scripts/**: Repository management scripts
- **docs/**: Documentation
- **.github/workflows/**: CI/CD automation
- **gh-pages branch**: Published APT repository content

## Related

- **Parent**: [../AGENTS.md](../AGENTS.md) - Workspace documentation
- **Packages**: Built from halos-marine-containers, cockpit-apt, runtipi-docker-service, etc.
