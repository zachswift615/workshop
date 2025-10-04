# Workshop

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

## Installation

```bash
pip install claude-workshop

# Set up Claude Code integration (recommended)
workshop init
```

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

## Data Storage

Workshop uses SQLite for fast, efficient storage:
- **Project-specific**: `./.workshop/workshop.db` in your project root
- **Global**: `~/.workshop/workshop.db` for cross-project context
- **Custom location**: Set `WORKSHOP_DIR` environment variable

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

### Utilities
- `workshop info` - Show workspace information
- `workshop init` - Set up Claude Code integration
- `workshop export` - Export context for web chat (with --recent, --context, --full options)

## License

MIT License - see LICENSE file for details.

## Contributing

Issues and pull requests welcome at https://github.com/zachswift615/workshop

