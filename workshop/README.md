# Workshop

Persistent context and memory tool for Claude Code sessions.

## Installation

```bash
pip install -e .

# Set up Claude Code integration (recommended)
workshop init
```

This will:
- Add Workshop instructions to global Claude Code settings (`~/.claude/settings.json`)
- Copy integration files to local project (`.claude/` directory)
- Enable automatic context loading at session start

### Manual Installation Options

```bash
# Global only (Claude checks for Workshop in all projects)
workshop init --global

# Local only (auto-load context in current project)
workshop init --local
```

## Quick Start

```bash
# Write entries
workshop note "Implemented user authentication flow"
workshop decision "Using zustand for state management" --reasoning "Simpler API than Redux, better TypeScript support"
workshop gotcha "Stripe webhooks need raw body parser disabled"
workshop preference "User prefers verbose comments explaining the why"

# Query and search
workshop why "using zustand"        # Smart search - answers "why did we do X?"
workshop context                    # Show current session context
workshop search "authentication"    # Search all entries
workshop read --type decision       # Show all decisions
workshop recent                     # Show recent entries

# Manage state
workshop goal add "Implement payment processing"
workshop next "Add error boundaries for auth failures"
```

## Data Storage

Workshop stores data in `.workshop/` directory:
- Project-specific: `./.workshop/` in your project root
- Global: `~/.workshop/` for cross-project context

## Claude Code Integration

Workshop integrates seamlessly with Claude Code to maintain context across sessions.

### Global Setup (Recommended)

Add Workshop instructions to your global Claude Code settings so it's available in all projects:

**Already done!** If you have `~/.claude/settings.json` configured, Claude will automatically:
- Check for Workshop at session start
- Use Workshop to record decisions, gotchas, and preferences
- Query Workshop for historical context

### Project-Specific Setup

For per-project integration with automatic context loading:

1. Copy `.claude/` directory from this repo to your project
2. The SessionStart hook will auto-load Workshop context
3. Custom instructions will guide Claude's Workshop usage

See `.claude/README.md` for details.

### How It Works

- **Session Start**: Claude checks if Workshop is available
- **During Session**: Claude records important information:
  - Architectural decisions with reasoning
  - Failed approaches and why
  - User preferences and coding style
  - Gotchas and constraints
  - Current goals and next steps
- **Context Queries**: Claude searches Workshop when needing historical context

### Benefits

- **Continuity**: Pick up exactly where you left off
- **Institutional Knowledge**: Never lose context about why things are the way they are
- **Collaboration**: Share context with future sessions (and future you!)
- **Efficiency**: Avoid re-discovering the same information
