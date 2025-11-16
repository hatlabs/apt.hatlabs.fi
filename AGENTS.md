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

## Issue Creation & Implementation

**MANDATORY:** All GitHub issues must require following `halos-distro/docs/IMPLEMENTATION_CHECKLIST.md` during implementation. Include this requirement in the issue body when creating issues.

## Development Workflow

**MANDATORY:** Follow `halos-distro/docs/DEVELOPMENT_WORKFLOW.md` for ALL implementations.

**Standard Workflow for All Features:**

1. **EXPLORE** - Read relevant code WITHOUT writing any code
   - Use `Task tool with subagent_type=Explore` for complex navigation
   - Reference relevant documentation
2. **PLAN** - Create implementation approach
   - Use `think hard` for planning
   - Document the plan before coding
3. **TEST** - Write tests FIRST (TDD)
   - Write comprehensive tests
   - Verify tests fail
   - Commit tests
4. **IMPLEMENT** - Code until tests pass
   - Follow the plan
   - Don't modify tests
   - Iterate until all pass
5. **VERIFY** - Check implementation quality
   - Use subagents for verification
   - Check for edge cases
6. **COMMIT** to a feature branch
7. **CREATE PR** and push to remote
8. **WAIT** for CI checks
9. **CHECK PR status** - verify tests pass, review feedback
10. **ITERATE** if needed, then merge

## Repository Structure

This repository maintains the Hat Labs APT repository at https://apt.hatlabs.fi.

- **scripts/**: Repository management scripts
- **docs/**: Documentation
- **.github/workflows/**: CI/CD automation
- **gh-pages branch**: Published APT repository content

## Related

- **Parent**: [../AGENTS.md](../AGENTS.md) - Workspace documentation
- **Packages**: Built from halos-marine-containers, cockpit-apt, runtipi-docker-service, etc.
