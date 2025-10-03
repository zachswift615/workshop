# Workshop

Persistent context and memory tool for Claude Code sessions.

## Installation

```bash
pip install -e .
```

## Quick Start

```bash
# Write entries
workshop note "Implemented user authentication flow"
workshop decision "Using zustand for state management" --reasoning "Simpler API than Redux, better TypeScript support"
workshop gotcha "Stripe webhooks need raw body parser disabled"
workshop preference "User prefers verbose comments explaining the why"

# Read and search
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
