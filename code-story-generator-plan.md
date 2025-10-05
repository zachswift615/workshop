# Code Story Generator

## Core Concept
A tool that analyzes git history and generates narrative summaries of how code evolved - turning commits into coherent stories.

## Vision
Transform the archaeological record of commits into actual narratives that capture not just chronology but *intention* - recognizing patterns like bug-fix cycles, experimental iterations, and architectural decisions.

## Key Features
1. **Trace a file/module's evolution** - Show how a specific piece of code changed over time and why
2. **Identify patterns** - Recognize bug-fix cycles, refactoring efforts, experimental iterations
3. **Connect the dots** - Link related commits that are part of the same "story arc"
4. **Generate readable narratives** - Turn technical diffs into human-readable explanations

## Tech Stack
- **TypeScript/Node.js** - Core logic
- **Git integration** - Parse history, diffs, commits
- **LLM integration** - Analyze commit messages and diffs to understand intent (Claude API)
- **CLI tool** - Start simple, make it easy to use

## First Milestone
Build a CLI that can take a file path in a git repo and generate a story of how it evolved.

## Future Possibilities
- Visualization layer for human consumption
- Multi-file story arcs
- Feature evolution tracking
- Interactive exploration
