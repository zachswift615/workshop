# Workshop

[![PyPI version](https://badge.fury.io/py/claude-workshop.svg)](https://pypi.org/project/claude-workshop/)
[![Tests](https://github.com/zachswift615/workshop/actions/workflows/test.yml/badge.svg)](https://github.com/zachswift615/workshop/actions/workflows/test.yml)
[![codecov](https://codecov.io/gh/zachswift615/workshop/branch/main/graph/badge.svg)](https://codecov.io/gh/zachswift615/workshop)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Give Claude Code long-term memory and project knowledge.**

Workshop is a production-ready context management system (using RAG - Retrieval-Augmented Generation) that gives Claude Code institutional memory. It automatically captures decisions, gotchas, and learnings from your conversations—and can even import months of past session history.

**Perfect for:** Persistent context, project knowledge base, fine-tuning training data, architectural decision records (ADR).

No manual note-taking. No context loss. Just continuous, persistent project knowledge.

---

## 🎯 Why Workshop?

**The Problem**: Claude Code has amazing conversations but terrible memory. Every new session starts from scratch. Your architectural decisions, lessons learned, and project context vanish after each compaction.

**The Solution**: Workshop gives Claude persistent memory. It automatically:
- 📝 **Records decisions** with reasoning as you discuss them
- ⚠️ **Documents gotchas** and constraints as you discover them
- 🔄 **Captures session summaries** when conversations end
- 🧠 **Answers "why" questions** by searching past decisions
- 📥 **Imports historical sessions** to backfill months of knowledge
- 🎯 **Tracks goals and blockers** across sessions
- 🔬 **Generates training data** for fine-tuning local LLMs (optional)

**Result**: Claude remembers everything about your project, even weeks or months later.

---

## ⚡ Quick Start

**Mac/Linux:**
```bash
pip install claude-workshop
workshop init
workshop import --execute  # Import your past sessions (optional)
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
workshop import --execute  # Import your past sessions (optional)
```

> **Note:** After installation on Windows, you must open a new terminal window for the `workshop` command to be available.

> **⚠️ Windows Limitation:** Automatic hooks are currently disabled on Windows due to Claude Code freezing issues. Workshop still works, but requires manual commands:
> - `workshop context` at session start
> - `workshop decision/gotcha/note` during work
> - `workshop import --execute` to capture sessions
>
> We're working to resolve this. Manual workflow is effective in the meantime!

That's it! Claude now has persistent memory in this project.

**In your next Claude Code session**, try:
```
"What decisions have we made about the database?"
"What gotchas should I know about?"
"What were we working on last session?"
```

Claude will search Workshop's knowledge base and give you context-aware answers.

---

## 🚀 Key Features

### 1. **Automatic Context Capture**
Claude automatically records important information as you work:
- Architectural decisions with reasoning
- Gotchas, constraints, and lessons learned
- Session summaries (what you worked on, files changed)
- User preferences and coding style
- Current goals and blockers

**You do nothing**—it just works.

### 2. **Historical Session Import** 🔥
The game-changer: Import your existing Claude Code conversation history.

```bash
workshop import --execute
```

Workshop analyzes past sessions using pattern matching to extract:
- Decisions: "We decided to use PostgreSQL because..."
- Gotchas: "Watch out for the rate limit on this API..."
- Discoveries: "Turns out the cache needs to be invalidated..."
- Summaries: Complete session summaries from compactions

**This means Workshop can learn from conversations you had weeks or months ago**, giving Claude instant access to all your project's history.

### 3. **Smart Search & Context**
Claude can query Workshop's knowledge base to answer questions:

```bash
workshop why "using zustand"     # Why did we choose this?
workshop search "authentication"  # Find all auth-related entries
workshop context                  # Current project state
workshop sessions                 # Past session summaries
```

Full-text search powered by SQLite FTS5 makes everything instantly retrievable.

### 4. **Per-Project Memory**
Each project gets its own knowledge base:
- Per-project `.workshop/workshop.db` database
- Auto-configuration via `~/.workshop/config.json`
- Works seamlessly across project directories
- Optional web UI for browsing (`workshop web`)

### 5. **Production-Ready**
- ✅ 63% test coverage (128 tests)
- ✅ Cross-platform (macOS, Linux, Windows)
- ✅ Schema migrations for upgrades
- ✅ Robust error handling
- ✅ Type-safe with comprehensive testing

---

## 📖 How It Works

### Setup (One-Time)

**Mac/Linux:**
```bash
pip install claude-workshop
workshop init
```

**Windows:** See [Quick Start](#-quick-start) above for Windows installation options (pipx recommended).

This configures Claude Code to:
1. Load Workshop context at session start
2. Record knowledge automatically during conversations
3. Capture session summaries at session end

### Automatic Operation

Once set up, Workshop works invisibly in the background:

**Session Start** → Claude loads project context from Workshop
**During Conversation** → Claude records decisions/gotchas as you discuss them
**Session End** → Workshop captures session summary automatically

### Manual Usage (Optional)

While Claude handles everything automatically, you can also:

```bash
# Query knowledge
workshop why "database choice"
workshop context
workshop recent

# Manually add entries
workshop decision "Using Redis for caching" -r "Need sub-millisecond latency"
workshop gotcha "API has 100 req/min rate limit"
workshop goal add "Implement retry logic"

# Import history
workshop import --execute
workshop import-status

# Manage entries
workshop search "authentication"
workshop delete <id>

# Admin
workshop info
workshop web  # Launch web UI
```

---

## 📥 Importing Historical Sessions

One of Workshop's most powerful features: **import months of past conversations**.

### Basic Import

```bash
# Preview what would be imported (safe, read-only)
workshop import

# Actually import sessions
workshop import --execute

# Check import status
workshop import-status
```

### Advanced Import

```bash
# Import specific file
workshop import ~/.claude/projects/my-project/session.jsonl --execute

# Interactive review (approve each extraction)
workshop import --interactive --execute

# See detailed extraction preview
workshop import --verbose
```

### What Gets Imported

Workshop uses intelligent pattern matching to extract:

- **Decisions**: "We chose X because Y"
- **Gotchas**: "Watch out for...", "Important to note..."
- **Discoveries**: "Found that...", "Turns out..."
- **Summaries**: Complete session summaries from compactions
- **Preferences**: User coding style and preferences

Each extraction includes:
- Confidence score (0.0-1.0)
- Source message UUID for traceability
- Timestamp for temporal context
- Automatic deduplication

### Import Intelligence

Workshop is smart about imports:
- ✅ Tracks what's been imported (no duplicates)
- ✅ Incremental imports (only new sessions)
- ✅ Handles compaction summaries (months of context)
- ✅ Filters noise (code snippets, JSON, hooks)
- ✅ Validates content quality before storing

---

## 🎨 Example Workflows

### Starting a New Session
```bash
claude  # Start Claude Code

# Claude automatically loads Workshop context:
# "📝 Workshop Context Available
#  Recent decisions: Using PostgreSQL, Zustand for state
#  Active goals: Implement caching layer
#  Gotchas: API rate limit 100/min..."
```

### Querying Past Decisions
```
You: "Why did we choose PostgreSQL over MongoDB?"

Claude: *searches Workshop* "According to the decision recorded 2 weeks ago,
you chose PostgreSQL because you needed ACID guarantees for transactions and
complex relational queries. The reasoning was that MongoDB's eventual
consistency wasn't suitable for financial data."
```

### Bootstrapping a Project
```bash
# You've been working in Claude Code for months
# Install Workshop and import everything:

pip install claude-workshop
workshop init
workshop import --execute

# Workshop now has months of project knowledge
# Claude can answer questions about past decisions immediately
```

---

## 🗂️ Entry Types

Workshop tracks different types of knowledge:

| Type | Icon | Purpose | Example |
|------|------|---------|---------|
| **decision** | 💡 | Architectural choices with reasoning | "Using PostgreSQL for ACID guarantees" |
| **note** | 📝 | General observations and findings | "API endpoint returns paginated results" |
| **gotcha** | ⚠️ | Constraints, limitations, warnings | "Rate limit is 100 requests per minute" |
| **preference** | 👤 | User coding style preferences | "Prefer async/await over promises" |
| **goal** | 🎯 | Current objectives | "Implement caching layer" |
| **blocker** | 🛑 | Issues preventing progress | "Waiting for API key from vendor" |
| **next_step** | 📍 | Immediate next actions | "Add error handling to login flow" |

---

## 📋 CLI Commands

### Query & Search
```bash
workshop why <query>           # Search decisions with reasoning
workshop search <query>        # Full-text search all entries
workshop browse <query>        # Search conversations with context
workshop context               # Show current project state
workshop recent                # Show recent entries
workshop sessions              # Show past session summaries
workshop info                  # Show workspace information
```

### Add Entries
```bash
workshop decision <text> -r <reasoning>  # Record decision
workshop note <text>                     # Add note
workshop gotcha <text>                   # Record gotcha
workshop preference <text>               # Record preference
workshop goal add <text>                 # Add goal
workshop blocker add <text>              # Add blocker
workshop next add <text>                 # Add next step
```

### Goals & Next Steps
```bash
workshop goal list              # Show all goals
workshop goal done <id>         # Mark goal complete
workshop next                   # Show next steps
workshop next done <id>         # Mark step complete
workshop next skip <id>         # Skip step
```

### Import & Export
```bash
workshop import                 # Preview import (read-only)
workshop import --execute       # Import sessions
workshop import <file> --execute  # Import specific file
workshop import --interactive   # Review each extraction
workshop import-status          # Show import history
workshop export                 # Export context for web chat
```

### Manage
```bash
workshop delete <id>            # Delete entry by ID
workshop clear <date>           # Delete entries before date
workshop web                    # Launch web UI (optional)
```

---

## 🔧 Configuration

Workshop uses `~/.workshop/config.json` for per-project settings:

```json
{
  "version": "1.0",
  "default_mode": "per-project",
  "projects": {
    "/Users/you/myproject": {
      "database": "/Users/you/myproject/.workshop/workshop.db",
      "jsonl_path": "~/.claude/projects/-Users-you-myproject",
      "auto_import": true
    }
  }
}
```

**Auto-configured on first use** - you typically don't need to edit this manually.

### Database Location

By default, Workshop stores data in `.workshop/workshop.db` at your project root.

You can customize per-project in the config, or use the optional web UI to manage settings.

---

## 🌐 Web UI (Optional)

Workshop includes an optional web interface:

```bash
workshop web
# Opens http://localhost:5001
```

Features:
- Browse all entries by type
- Full-text search
- Edit and delete entries
- View session summaries
- Manage configuration

Great for exploring Workshop's knowledge base visually!

---

## 🔍 JSONL File Locations

Workshop imports from Claude Code's JSONL session files:

**macOS/Linux:**
```
~/.claude/projects/<normalized-project-path>/
```

**Windows:**
```
%USERPROFILE%\.claude\projects\<normalized-project-path>\
```

**Path Normalization:**
- `/Users/name/project` → `-Users-name-project`
- Underscores in project names are preserved

Workshop auto-detects the correct location. If import can't find files, it provides platform-specific troubleshooting.

---

## 🤝 Integration with Claude Code

Workshop provides three integration points:

### 1. Session Start Hook
Loads project context when Claude Code starts:
```bash
~/.claude/projects/myproject/workshop-session-start.sh
```

### 2. Session End Hook
Captures session summary when Claude Code exits:
```bash
~/.claude/projects/myproject/workshop-session-end.sh
```

### 3. Pre-Compact Hook
Preserves context before compaction:
```bash
~/.claude/pre-compact/workshop-pre-compact.sh
```

**All hooks are set up automatically by `workshop init`.**

---

## 📊 Why the Test Coverage Matters

Workshop has **63% test coverage** with **128 tests** across:
- JSONL parsing and pattern extraction (95% coverage)
- SQLite storage operations (75% coverage)
- Configuration management (98% coverage)
- Display and formatting (27% coverage - mostly console I/O)

This isn't just for show—it means:
- ✅ Reliable imports that won't corrupt your data
- ✅ Safe schema migrations when upgrading
- ✅ Consistent behavior across platforms
- ✅ Confidence that Workshop won't lose your knowledge

**Production-ready means tested.**

---

## 📝 Example Use Cases

### 1. **Architectural Decision Records**
```bash
# Claude automatically captures these during conversations
workshop why "microservices"

# Output:
# 💡 DECISION (2 weeks ago)
# Using microservices architecture for backend
# Why: Need independent scaling of services, team prefers polyglot approach
```

### 2. **Onboarding New Team Members**
```bash
workshop context
workshop sessions --limit 10

# New devs can see entire project history:
# - What decisions were made and why
# - What gotchas to avoid
# - Current architecture and patterns
```

### 3. **Debugging Production Issues**
```bash
workshop search "authentication flow"

# Instantly find all discussions about auth:
# - Original implementation decisions
# - Known gotchas with OAuth
# - Recent changes to token handling
```

### 4. **Resuming After Time Away**
```bash
# After weeks off the project:
workshop recent
workshop context

# Claude: "Welcome back! Since your last session:
#  - Completed caching implementation
#  - Discovered rate limiting issue with API
#  - Next step: Add retry logic with exponential backoff"
```

---

## 🧠 Advanced Uses

### RAG (Retrieval-Augmented Generation)

Workshop is a **RAG system** for Claude Code. Unlike Claude Projects (web) which has built-in RAG, Claude Code (CLI) doesn't provide persistent context across sessions. Workshop fills this gap by:

- **Automatic retrieval**: Session hooks load relevant context when Claude starts
- **Smart search**: Full-text search (SQLite FTS5) retrieves relevant entries
- **Context preservation**: Decisions, gotchas, and learnings persist across sessions
- **No token overhead**: Only relevant context is included (not entire knowledge base)

**Workshop gives Claude Code the same RAG capabilities that Claude Projects has**, optimized for CLI workflows.

### Fine-tuning Training Data

Your Workshop entries are **perfect training data** for fine-tuning local LLMs:

- **Decisions with reasoning** → Q&A pairs ("Why did we choose X?" → "Because Y")
- **Gotchas** → Domain-specific constraints and warnings
- **Preferences** → Coding style and architectural patterns
- **Session summaries** → Project evolution and context

Check out [`finetune/`](./finetune) for a complete pipeline to:
1. **Generate training data** from your codebase + Workshop entries
2. **Fine-tune Qwen 2.5 Coder 7B** (or similar) using LoRA
3. **Run locally** on consumer GPUs (RTX 4060 works!)

**Two approaches:**
- **RAG** (Workshop): Retrieve knowledge at query time
- **Fine-tuning**: Bake knowledge into model weights

**Best results**: Use both! Fine-tune for architectural patterns, use Workshop for latest decisions.

See [finetune/QUICKSTART.md](./finetune/QUICKSTART.md) for a step-by-step guide.

---

## 🎯 Roadmap

Workshop v1.0.0 is feature-complete for core use cases. Future possibilities:

- **Team Sync**: Share Workshop knowledge across team members
- **Slack/Discord Integration**: Bot that answers project questions
- **GitHub Integration**: Link decisions to PRs and issues
- **Advanced Analytics**: Visualize decision timelines
- **AI-Powered Summaries**: Automatically generate weekly summaries

Have ideas? [Open an issue](https://github.com/zachswift615/workshop/issues/new/choose) or start a [discussion](https://github.com/zachswift615/workshop/discussions)!

---

## 📚 Documentation

- [CHANGELOG.md](CHANGELOG.md) - Version history and release notes
- [GitHub Issues](https://github.com/zachswift615/workshop/issues) - Bug reports and feature requests
- [GitHub Discussions](https://github.com/zachswift615/workshop/discussions) - Questions and ideas

---

## 🤝 Contributing

We welcome contributions! If you find a bug or have a feature request, please [open an issue](https://github.com/zachswift615/workshop/issues/new/choose).

**For bug reports**, please include:
- Workshop version (`pip show claude-workshop`)
- Python version (`python --version`)
- Operating system
- Steps to reproduce
- Error messages or logs

**Pull requests** are welcome! For major changes, please open an issue first to discuss.

---

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

Built with [Claude Code](https://claude.ai/code) - an AI pair programmer that needed better memory. Workshop exists because developers and AI assistants both benefit from persistent context.

**Workshop is for Claude, by Claude (and humans who want their AI to remember).**

---

## ⭐ Star History

If Workshop helps your workflow, consider starring the repo to help others discover it!

[![Star History Chart](https://api.star-history.com/svg?repos=zachswift615/workshop&type=Date)](https://star-history.com/#zachswift615/workshop&Date)

---

**Ready to give Claude long-term memory?**

```bash
pip install claude-workshop && workshop init
```

🚀 That's it. Claude now remembers everything.
