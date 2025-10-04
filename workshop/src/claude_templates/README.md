# Claude Code Integration for Workshop

This directory contains Claude Code configuration to integrate Workshop into Claude sessions.

## Files

### `settings.json`
Main configuration file that:
- **Hooks**: Runs `workshop context` at session start to load project context
- **Custom Instructions**: Tells Claude to use Workshop liberally throughout sessions

### `workshop-session-start.sh`
SessionStart hook script that displays Workshop context at the beginning of each Claude session.

### `commands/workshop.sh`
Slash command wrapper for Workshop CLI (if slash commands are supported in your Claude Code version).

## How It Works

1. **Session Start**: When you start a new Claude Code session, the SessionStart hook automatically runs `workshop context` to show recent decisions, goals, gotchas, and preferences.

2. **Custom Instructions**: Claude is instructed to use Workshop throughout the session to:
   - Record architectural decisions with reasoning
   - Document gotchas and constraints
   - Track goals and next steps
   - Save user preferences
   - Note failed approaches

3. **Persistent Context**: All Workshop data is stored in `.workshop/` (gitignored) so context persists across sessions but stays private.

## Usage

Once configured, Claude will automatically:
- Load Workshop context at session start
- Use Workshop commands to record important information
- Query Workshop for historical context when needed

You can also manually run Workshop commands:
```bash
workshop context
workshop decision "Using X because Y" -r "reasoning here"
workshop gotcha "Watch out for Z" -t tag1 -t tag2
workshop search "authentication"
```

## Installation

1. Ensure Workshop is installed: `pip install -e ./workshop`
2. The `.claude/` configuration is already set up in this project
3. Start a new Claude Code session - Workshop context will load automatically!

## Customization

Edit `settings.json` to customize:
- Which hooks run at session start
- Custom instructions for how Claude uses Workshop
- Hook behavior (startup vs resume vs clear)
