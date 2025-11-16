# Hat Labs APT repository

This is the APT repository for Hat Labs. It contains packages and tools for use with our systems.

## Agentic Coding Setup (Claude Code, GitHub Copilot, etc.)

For development with AI assistants, use the halos-distro workspace for full context:

```bash
# Clone the workspace
git clone https://github.com/hatlabs/halos-distro.git
cd halos-distro

# Get all sub-repositories including apt.hatlabs.fi
./run repos:clone

# Work from workspace root for AI-assisted development
# Claude Code gets full context across all repos
```

See `halos-distro/docs/` for development workflows:
- `HUMAN_DEVELOPMENT_GUIDANCE.md` - Quick start guide
- `IMPLEMENTATION_CHECKLIST.md` - Development checklist
- `DEVELOPMENT_WORKFLOW.md` - Detailed workflows
