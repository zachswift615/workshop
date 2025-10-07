#!/usr/bin/env python3
"""
Prepare Workshop codebase for fine-tuning.
Creates conversation-style training examples from code + docs + workshop entries.
"""
import json
from pathlib import Path
import sqlite3


def extract_code_examples():
    """Extract meaningful code snippets with explanations."""
    examples = []

    # Example: Storage layer
    examples.append(
        {
            "instruction": "How does Workshop store entries in the database?",
            "context": "Workshop uses SQLAlchemy ORM with support for both SQLite and PostgreSQL.",
            "response": """Workshop stores entries using the EntriesManager class in src/storage/entries.py.

Key methods:
- add_entry(): Creates new entries with type, content, reasoning, tags, and files
- get_entries(): Retrieves entries with optional filtering by type, tags, limit
- search(): Full-text search across entry content
- update_entry(): Modifies existing entries
- delete_entry(): Removes entries by ID

Entries are stored in the 'entries' table with fields:
- id (UUID primary key)
- project_id (for multi-tenant support)
- type (note, decision, gotcha, preference, etc.)
- content (main text)
- reasoning (optional explanation)
- timestamp (UTC datetime)
- branch, commit_hash (git context)
- entry_metadata (JSON blob)

Related tables: tags, files (many-to-many relationships)""",
        }
    )

    # Example: CLI structure
    examples.append(
        {
            "instruction": "What CLI commands does Workshop provide?",
            "context": "Workshop uses Click framework for CLI",
            "response": """Workshop CLI commands (src/cli.py):

**Write commands:**
- workshop note "text" - Add a note
- workshop decision "text" -r "reasoning" - Record decision
- workshop gotcha "text" - Document constraint/gotcha
- workshop preference "text" --category - Save preference

**State management:**
- workshop goal add/list/clear/done/clean - Manage goals
- workshop next add/done/clean - Manage next steps

**Query commands:**
- workshop search "query" - Search entries
- workshop why "query" - Answer why questions (prioritizes decisions)
- workshop recent - Show recent entries
- workshop context - Show session summary

**Session commands:**
- workshop sessions - List past sessions
- workshop session <id/last> - View session details

**Other:**
- workshop web - Launch web UI
- workshop export - Export context
- workshop import - Import from JSONL transcripts""",
        }
    )

    return examples


def extract_architecture_knowledge():
    """Extract architectural decisions and patterns."""
    examples = []

    examples.append(
        {
            "instruction": "Explain Workshop's architecture",
            "context": "Workshop is a context management tool for Claude Code",
            "response": """Workshop Architecture:

**Core Components:**
1. Storage Layer (src/storage/)
   - base.py: DatabaseManager (SQLite/PostgreSQL)
   - entries.py: Entry CRUD operations
   - sessions.py: Session tracking
   - preferences_state.py: User preferences & current state

2. CLI Layer (src/cli.py)
   - Click-based command interface
   - 40+ commands for context management

3. Display Layer (src/display.py)
   - Rich terminal output using 'rich' library
   - Formatted tables, panels, markdown

4. Web UI (src/web/)
   - Flask application
   - View/edit entries via browser

5. JSONL Import (src/jsonl_parser.py)
   - Extract context from Claude Code transcripts
   - Pattern matching + optional LLM extraction

**Key Design Decisions:**
- UTC timestamps (naive) stored, converted to local for display
- SQLAlchemy ORM for database abstraction
- Project detection via .git, package.json, pyproject.toml
- Workspace can be per-project or global""",
        }
    )

    return examples


def extract_workshop_entries(db_path):
    """Extract actual workshop entries as training examples."""
    examples = []

    if not db_path.exists():
        return examples

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get decisions with reasoning (most valuable)
    cursor.execute(
        """
        SELECT content, reasoning
        FROM entries
        WHERE type = 'decision' AND reasoning IS NOT NULL
        LIMIT 20
    """
    )

    for content, reasoning in cursor.fetchall():
        examples.append(
            {
                "instruction": f"Why did we decide to {content.lower()}?",
                "context": "Workshop project decision",
                "response": f"Decision: {content}\n\nReasoning: {reasoning}",
            }
        )

    # Get gotchas (important constraints)
    cursor.execute(
        """
        SELECT content
        FROM entries
        WHERE type = 'gotcha'
        LIMIT 10
    """
    )

    for (content,) in cursor.fetchall():
        examples.append(
            {
                "instruction": "What should I watch out for in Workshop?",
                "context": "Workshop project gotcha",
                "response": f"Gotcha: {content}",
            }
        )

    conn.close()
    return examples


def format_for_training(examples):
    """Convert to format suitable for fine-tuning."""
    training_data = []

    for ex in examples:
        # Alpaca format (common for instruction tuning)
        formatted = {"instruction": ex["instruction"], "input": ex.get("context", ""), "output": ex["response"]}
        training_data.append(formatted)

    return training_data


def main():
    output_dir = Path(__file__).parent
    output_dir.mkdir(exist_ok=True)

    print("Extracting training examples...")

    # Gather examples
    examples = []
    examples.extend(extract_code_examples())
    examples.extend(extract_architecture_knowledge())

    # Add workshop entries if available
    db_path = Path(__file__).parent.parent / ".workshop" / "workshop.db"
    if db_path.exists():
        examples.extend(extract_workshop_entries(db_path))
        print(f"  Added {len(extract_workshop_entries(db_path))} entries from database")

    # Format for training
    training_data = format_for_training(examples)

    # Save as JSONL (one JSON object per line)
    output_file = output_dir / "workshop_training.jsonl"
    with open(output_file, "w") as f:
        for item in training_data:
            f.write(json.dumps(item) + "\n")

    print(f"\n✓ Created {len(training_data)} training examples")
    print(f"✓ Saved to: {output_file}")
    print("\nNext steps:")
    print(f"  1. Review {output_file} and add more examples")
    print("  2. Run finetune.py to train the model")


if __name__ == "__main__":
    main()
