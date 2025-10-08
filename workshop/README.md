# Workshop

[![PyPI version](https://badge.fury.io/py/claude-workshop.svg)](https://pypi.org/project/claude-workshop/)
[![Tests](https://github.com/zachswift615/workshop/actions/workflows/test.yml/badge.svg)](https://github.com/zachswift615/workshop/actions/workflows/test.yml)
[![codecov](https://codecov.io/gh/zachswift615/workshop/branch/main/graph/badge.svg)](https://codecov.io/gh/zachswift615/workshop)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Give Claude long-term memory for your projects.**

Workshop is a persistent memory tool that lets Claude Code remember your decisions, preferences, and project context across sessions. Install it once, and Claude automatically maintains institutional knowledge about your codebase - no manual note-taking required.

**For developers using Claude Code** - your AI pair programmer will remember why you made architectural choices, what gotchas to avoid, and what you're working on, even weeks later.

## How It Works

1. **You install Workshop**: `pip install claude-workshop`
2. **You run setup once**: `workshop init`
3. **Claude does everything else**: Records decisions, maintains context, answers "why" questions

Claude automatically:
- 📝 Records architectural decisions with reasoning as you discuss them
- ⚠️ Documents gotchas and constraints as you discover them
- 🔄 Captures session summaries (files changed, commands run, what you worked on)
- 🧠 Answers "why did we choose X?" questions by searching past decisions
- 🎯 Tracks your current goals and next steps
- 🔍 Provides full-text search across all project knowledge
- 📥 **NEW:** Imports historical Claude Code sessions to backfill knowledge

## Installation

**Mac/Linux:**
```bash
pip install claude-workshop
workshop init
```

**Windows:**

> **Requirements:** Git Bash (included with Claude Code installation)

```bash
pip install claude-workshop

# Add workshop to PATH permanently:
echo 'export PATH="$(python -c \"import site; print(site.USER_BASE)\")/Scripts:$PATH"' >> ~/.bashrc
source ~/.bashrc

# Then open a new terminal and run:
workshop init
```

> **Note:** After installation on Windows, you must open a new terminal window for the `workshop` command to be available.

> **⚠️ Windows Limitation:** Automatic hooks (SessionStart/SessionEnd) are currently disabled on Windows due to Claude Code freezing issues. Workshop still works great, but you'll need to manually run commands:
> - Start sessions: `workshop context` to load existing knowledge
> - During work: Use `workshop decision`, `workshop gotcha`, etc. as needed
> - End sessions: `workshop import --execute` to capture session summaries from transcripts
>
> We're working with Anthropic to resolve the hook freezing issue. In the meantime, manual workflow works well!

This sets up Claude Code integration:
- **Global**: Adds Workshop instructions to `~/.claude/settings.json` (Claude will use Workshop in all your projects)
- **Local**: Copies integration files to `.claude/` (auto-loads context at session start, captures session summaries at session end)

That's it! Start a new Claude Code session and Claude will automatically maintain your project's institutional knowledge.

### What Gets Set Up

The `workshop init` command configures Claude Code to:
- Load existing context at the start of each session
- Record decisions, gotchas, and preferences as you work
- Capture session summaries automatically when sessions end
- Answer "why" questions by searching past decisions

## What You Can Do (Optional)

While Claude handles most Workshop interactions automatically, you can also use the CLI directly:

```bash
# Query what Claude has learned
workshop why "using zustand"        # Why did we make this choice?
workshop context                    # What's the current project state?
workshop sessions                   # What happened in past sessions?
workshop recent                     # What was recorded recently?

# Manually add entries (though Claude does this automatically)
workshop decision "Using PostgreSQL" -r "Need ACID guarantees for transactions"
workshop gotcha "API rate limit is 100 req/min"
workshop goal add "Implement caching layer"
```

**Most users never need to run these commands** - just let Claude manage everything!

### Import Historical Sessions (NEW in v0.2.0!)

Bootstrap Workshop with knowledge from past Claude Code sessions:

```bash
# Import current project's history
workshop import                 # Preview what would be imported
workshop import --execute       # Actually import historical sessions

# Import specific files
workshop import session.jsonl --execute

# Interactive review
workshop import --interactive --execute

# Check what's been imported
workshop import-status
```

Workshop automatically:
- Extracts decisions, gotchas, and preferences from past conversations
- Tracks what's been imported to avoid duplicates
- Incrementally imports new sessions as they're created
- Uses pattern matching to identify valuable knowledge

### Export for Web Chat

Want to continue a conversation in Claude.ai web chat with full context from your Claude Code sessions?

```bash
workshop export              # Export last month of context
workshop export --recent     # Export last week only
workshop export --context    # Export just current goals/state
workshop export --full       # Export everything including notes
workshop export -o context.md # Save to file
```

Copy the output and paste it into a web chat to give Claude continuity between Code and web sessions!

### Web Admin Interface

Workshop includes a web-based admin interface for browsing and managing your knowledge base:

```bash
# Start the web server (requires Flask)
pip install "claude-workshop[web]"
workshop web

# Custom port
workshop web --port 8080
```

Then open http://localhost:5000 in your browser.

**Features:**
- **Dashboard**: Stats and recent entries
- **Browse**: Searchable, filterable list of all entries
- **View/Edit**: Click any entry to view details or make edits
- **Delete**: Remove outdated or incorrect entries
- **Settings**: View and edit your `~/.workshop/config.json`

The Settings page lets you:
- View/edit configuration with syntax highlighting
- Register new projects manually
- Validate configuration and test paths
- See auto-detected vs manually configured projects

## Data Storage

Workshop uses SQLite for fast, efficient storage:

### Database Locations

Workshop automatically finds the right database location using this priority order:

1. **Auto-detected** (default): `.workshop/workshop.db` at your git root
2. **Fallback**: `.workshop/workshop.db` in current directory
3. **Custom**: Configure via `~/.workshop/config.json` (see Configuration below)

### Claude Code Session Files (JSONL)

Claude Code stores conversation transcripts that Workshop can import:

**macOS & Linux:**
```
~/.claude/projects/<normalized-project-path>/*.jsonl
```
Example: `/Users/name/my-project` → `~/.claude/projects/-Users-name-my-project/*.jsonl`

**Windows:**
```
%USERPROFILE%\.claude\projects\<normalized-project-path>\*.jsonl
```
Example: `C:\Users\name\my-project` → `%USERPROFILE%\.claude\projects\C-Users-name-my-project\*.jsonl`

**Path Normalization:**
- Forward slashes (`/`) become hyphens (`-`)
- Underscores (`_`) become hyphens (`-`)
- Drive letters are preserved on Windows

### Configuration File

Workshop supports a global config file at `~/.workshop/config.json`:

```json
{
  "version": "1.0",
  "default_mode": "per-project",
  "projects": {
    "/Users/name/my-project": {
      "database": "/Users/name/my-project/.workshop/workshop.db",
      "jsonl_path": "~/.claude/projects/-Users-name-my-project",
      "auto_import": true
    }
  },
  "global": {
    "database": "~/.workshop/workshop.db",
    "enabled": false
  }
}
```

The config file:
- Auto-registers projects when you first use Workshop in them
- Allows manual overrides for database and JSONL locations
- Can be edited via the Web UI (see Web Admin Interface below)

### Migration from JSON

If you're upgrading from an earlier version that used JSON storage, Workshop will automatically migrate your data to SQLite on first run and create a backup of your JSON file.

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


## Commands Reference

### Write Entries
- `workshop note <text>` - Add a note
- `workshop decision <text> -r <reasoning>` - Record a decision with reasoning  
- `workshop gotcha <text>` - Document a gotcha or constraint
- `workshop preference <text>` - Save a user preference
- `workshop antipattern <text>` - Record an antipattern to avoid

### Query & Search
- `workshop why <query>` - Smart search answering "why did we do X?"
- `workshop search <query>` - Full-text search across all entries
- `workshop context` - Show current session context summary
- `workshop recent` - Show recent entries
- `workshop read --type <type>` - Filter entries by type

### Session History
- `workshop sessions` - List recent sessions
- `workshop session <id|last>` - View session details

### State Management
- `workshop goal add <text>` - Add a goal
- `workshop goal list` - List active goals
- `workshop goal done <text>` - Mark a goal as completed
- `workshop goal clean` - Remove completed goals
- `workshop next add <text>` - Add a next step/TODO
- `workshop next done <text>` - Mark a next step as completed
- `workshop next clean` - Remove completed next steps

### Delete & Clean
- `workshop delete <id>` - Delete an entry by ID
- `workshop delete last` - Delete the most recent entry
- `workshop clean` - Interactively delete entries (last 7 days)
- `workshop clean --type <type>` - Clean only specific entry type
- `workshop clean --days <n>` - Clean entries from last N days
- `workshop clear <date>` - Delete all entries before date (e.g., "2025-01-01" or "30 days ago")
- `workshop clear <date> --type <type>` - Delete entries of specific type before date

### Import & Export
- `workshop import` - Import historical JSONL sessions (preview mode)
- `workshop import --execute` - Actually import sessions
- `workshop import <file.jsonl>` - Import specific file
- `workshop import --interactive` - Review each extraction
- `workshop import-status` - Show import history
- `workshop export` - Export context for web chat (with --recent, --context, --full options)

### Utilities
- `workshop info` - Show workspace information
- `workshop init` - Set up Claude Code integration

## License

MIT License - see LICENSE file for details.

## Contributing

Issues and pull requests welcome at https://github.com/zachswift615/workshop

