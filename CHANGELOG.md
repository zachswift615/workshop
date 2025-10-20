# Changelog

All notable changes to Workshop will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.8.0] - 2025-10-20

### Added
- add line about browse
- Add conversation browsing and message type filtering features
- Add collapse/expand for long messages in conversation view
- Add Claude Code TUI-style conversation view
- Add tool result/use content display in web UI
- Add raw message storage for complete conversation history

### Fixed
- Fix message type detection to properly identify tool results and tool uses
- Fix: Preserve all content in raw message storage by skipping noise filter

### Changed
- updated test

### Other
- more scip igoring
- ignore scip index


## [2.7.0] - 2025-10-08

### Fixed
- Fix duplicate hook execution - only write hooks to settings.local.json


## [2.6.0] - 2025-10-08

### Other
- Disable hooks on Windows due to Claude Code freezing issues


## [2.5.0] - 2025-10-07

### Other
- Simplify Windows support: require bash (Git Bash) instead of batch files
- Use bash scripts with 'bash' prefix on Windows when Git Bash is available


## [2.4.2] - 2025-10-07

### Added
- Add Git Bash PATH setup instructions for Windows

### Fixed
- Fix Windows hook paths to use absolute paths instead of relative


## [2.4.1] - 2025-10-07

### Changed
- Update root README with Windows installation instructions

### Other
- Remove pipx installation instructions


## [2.4.0] - 2025-10-07

### Added
- Add Windows PATH setup commands and clean up imports
- Add Windows support and fix critical hook priority bug

### Other
- Remove Windows setup documentation - now fully automatic


## [2.3.2] - 2025-10-07

### Fixed
- Fix timestamp parsing bug with Z suffix in Claude Code JSONL files


## [2.3.1] - 2025-10-07

### Fixed
- Fix lint errors in finetune directory


## [2.3.0] - 2025-10-07

### Added
- Add fine-tuning capabilities to Workshop

### Changed
- Improve test coverage from 59% to 75% and fix clear command bug


## [2.2.9] - 2025-10-06

### Added
- Add regression test for UTC timestamp display bug

### Fixed
- Fix: Convert UTC timestamps to local time for display


## [2.2.8] - 2025-10-06

### Added
- Add regression tests for web UI edit and delete functionality

### Fixed
- Fix: Web UI edit and delete routes to use SQLAlchemy instead of raw SQL


## [2.2.7] - 2025-10-06

### Fixed
- Fix: Add UTF-8 encoding to test file read for Windows compatibility


## [2.2.6] - 2025-10-06

### Added
- Add import guidance to CLAUDE.md for better discoverability

### Fixed
- Fix: Add version parameter to web UI URL for cache busting
- Fix: Change default port to 5001 and add meta cache-control tags


## [2.2.5] - 2025-10-06

### Fixed
- Fix: Add cache-control headers to prevent persistent 403 errors


## [2.2.4] - 2025-10-06

### Fixed
- Fix: Web UI AttributeError and improve Flask install error message


## [2.2.3] - 2025-10-06

### Fixed
- Fix: Always update hook scripts on workshop init


## [2.2.2] - 2025-10-06

### Fixed
- Fix: Simplify SessionStart hook - remove Python and background processes


## [2.2.1] - 2025-10-06

### Fixed
- Fix: Use relative paths for hook commands instead of ${CLAUDE_PROJECT_DIR}


## [2.2.0] - 2025-10-06

### Fixed
- Fix: Replace customInstructions with CLAUDE.md and add hook permissions


## [2.1.0] - 2025-10-05

### Fixed
- Fix: Create settings.local.json during workshop init


## [2.0.3] - 2025-10-05

### Added
- Add auto-initialization for Workshop in new projects


## [2.0.2] - 2025-10-05

### Changed
- Improve release.sh: test with editable install to catch packaging issues

### Other
- Remove backup file and add backup patterns to gitignore


## [2.0.1] - 2025-10-05

### Fixed
- Fix packaging: include src.storage package in distribution


## [2.0.0] - 2025-10-05

### Added
- Add workshop-client as optional cloud dependency

### Fixed
- Fix tests: update for new SQLAlchemy storage architecture

### Changed
- Refactor storage layer to modular SQLAlchemy architecture


## [1.1.0] - 2025-10-05

### Added
- Add SessionStart hook for resume source
- Add retry logic for PyPI propagation delay

### Fixed
- Fix test_changes_to_project_root for new workspace prompt

### Other
- Replace workspace detection with config-first + weighted heuristics


## [1.0.6] - 2025-10-05

### Added
- Add non-interactive mode to release script
- Add automated release script

### Fixed
- Fix test_llm_extraction_without_client when API key in env
- Fix version display and session hook reliability

### Changed
- Update CHANGELOG for v1.0.5

### Other
- Move release script to project root


## [1.0.5] - 2025-01-05

### Added
- **LM Studio support**: Local LLM extraction as FREE alternative to Anthropic API
  - New `--llm-local` flag for using local LLM servers (LM Studio, etc.)
  - New `--llm-endpoint` option to customize local LLM endpoint (default: http://localhost:1234/v1)
  - OpenAI-compatible client integration for local models
  - Automatic server detection with helpful setup instructions if not running
  - Cost display shows "FREE (running locally)" for local LLM extraction
  - Recommended models documented: Mistral 7B, Llama 3.1 8B, Qwen 2.5 7B
  - Same extraction quality as API with good local models
- **Test coverage**: 10 new comprehensive unit tests for LLM extraction
  - API client initialization tests
  - Mocked LLM response handling
  - Fallback behavior verification
  - Error handling (API errors, malformed JSON)
  - Edge cases (short messages, missing dependencies)

### Fixed
- **Critical workspace isolation bug**: Non-git projects under home directory were incorrectly using `~/.workshop` instead of creating local `.workshop` directory
  - Caused all projects under home to share global database, breaking per-project isolation
  - Fixed by stopping upward directory search before reaching home directory
  - Each project now gets proper isolation (git repos: `.workshop` at git root, non-git: `.workshop` in current directory)
- **Cost estimation bug**: Import cost estimation was using Sonnet pricing ($3/M input, $15/M output) instead of Haiku pricing ($0.25/M input, $1.25/M output)
  - This caused estimates to be 12x too high (e.g., $580 instead of $48)
  - Now correctly shows Haiku pricing for `--llm` flag

### Changed
- Users now have 3 extraction options for JSONL import:
  1. Pattern matching (free, default, good quality)
  2. Anthropic API with `--llm` (paid, excellent quality, ~$48 for 18k messages)
  3. **LM Studio with `--llm-local` (FREE, excellent quality, offline, private)**
- Updated optional dependencies: added `openai>=1.0.0` to `llm` extras

## [1.0.4] - 2025-01-04

### Improved
- **Search ranking**: Dramatically improved `workshop why` command to surface most relevant answers first
  - Keyword occurrence counting (not just presence)
  - Reasoning length boost for more complete explanations
  - Tag count boost for curated entries
  - "Why" indicator boost for entries with "provides", "enables", "better", etc.
  - BM25 ranking for better FTS5 relevance in regular search

### Fixed
- Fixed AttributeError when entries have null reasoning field in why_search

## [1.0.3] - 2025-01-04

### Fixed
- **Search query bug**: Fixed crash when searching for terms with hyphens (e.g., "auto-attachment"). FTS5 queries now properly handle special characters by normalizing hyphens to spaces.
- **Error display**: Search errors now show user-friendly messages instead of Python tracebacks
- **Session hook context**: Fixed truncated/empty context display in session start hook by using proper JSON escaping

### Added
- **Search filters**: Added `--type` option to filter search results by entry type (note/decision/gotcha/preference/goal/next)
- **Search formatting**: Added `--format` option for compact or full display of search results
- **Fallback search**: Implemented LIKE-based fallback search when FTS5 queries fail
- **Test coverage**: Added 4 comprehensive tests for special character search handling

## [1.0.2] - 2025-01-04

### Added
- **Auto-cd to project root**: Workshop commands now automatically change to the project root (parent of `.workshop/`) when executed. This prevents Claude Code from creating nested `.workshop` directories when running commands from subdirectories.
- Test coverage for auto-cd feature (`test_changes_to_project_root`)

### Changed
- Implemented `_change_to_project_root()` helper function to ensure consistent workspace behavior across all CLI commands

## [1.0.1] - 2025-01-04

### Fixed
- **Web UI workspace bug**: Web UI now correctly shows data from the workspace where `workshop web` was launched. Previously, when running `workshop web` in one project and then switching to another project and running it again, the UI would show the first project's data instead of the current project's.
- CLI now explicitly passes `workspace_dir` to Flask app to ensure correct workspace binding
- Added warning message to web UI startup explaining workspace behavior

### Added
- Regression test for web UI workspace bug (`test_web_command_passes_workspace`)

## [1.0.0] - 2025-01-04 🎉

### 🚀 Production Release

Workshop v1.0.0 marks the transition from prototype to production-ready software. This release represents a complete, tested, and polished context management system for Claude Code.

**Why v1.0.0?**
- ✅ Complete feature set for core use cases
- ✅ Production-grade reliability (63% test coverage, 128 tests)
- ✅ Battle-tested JSONL import system
- ✅ Cross-platform support with CI/CD
- ✅ Comprehensive documentation and examples
- ✅ Stable API ready for long-term use

### Added
- **Completely rewritten README** with:
  - Clear problem/solution framing
  - Prominent Quick Start section
  - Detailed feature explanations with examples
  - Multiple workflow examples
  - Comprehensive CLI reference
  - Production-ready positioning
- **GitHub issue templates** (bug reports, feature requests)
- **CHANGELOG.md** with complete version history
- **Roadmap section** for future enhancements

### Changed
- **Documentation overhaul** to emphasize:
  - Historical session import as killer feature
  - Production-ready status with test coverage
  - Real-world use cases and workflows
  - Clear value proposition for developers

### Highlights from v0.x Journey

**The Path to v1.0.0:**
- v0.1.0: Initial release with core CRUD operations
- v0.2.0: **Game-changer** - JSONL import feature added
- v0.3.0: Configuration system and web UI
- v0.3.4: Test coverage pushed to 63%
- v1.0.0: **Production-ready** - polished, tested, documented

**What Makes Workshop Production-Ready:**
1. **Automatic JSONL Import** - Backfill months of conversation history
2. **Robust Testing** - 128 tests, 63% coverage, CI across platforms
3. **Smart Extraction** - Pattern matching with confidence scoring
4. **Reliable Storage** - SQLite with FTS5, schema migrations
5. **Seamless Integration** - Auto-configured Claude Code hooks
6. **Professional Polish** - Documentation, issue templates, changelog

## [0.3.4] - 2025-01-04

### Added
- Comprehensive test coverage (128 tests, 51% coverage locally / 63% on Codecov)
- 45 comprehensive tests for jsonl_parser module (34% → 95% coverage)
- 22 tests for display module (timestamp formatting and emoji functions)
- Coverage configuration in pyproject.toml with exclusions for non-core files

### Fixed
- **Critical bug**: Tool error extraction was blocked by early return on empty content
- Test assertions to match actual pattern requirements (e.g., "chose to" vs "chose")

### Changed
- Moved tool error extraction before content check in jsonl_parser
- Improved test coverage for all extraction methods (compaction summaries, decisions, gotchas, preferences)
- Added edge case testing for timestamp formatting (timezone-aware, boundaries)

## [0.3.3] - 2025-01-04

### Added
- Comprehensive test coverage (71 tests, 43% coverage)
- CLI integration tests revealing global storage state bug
- Expanded JSONL parser tests

### Fixed
- Timezone bug in display.py causing `workshop context` to crash
- GitHub Actions coverage reporting (--cov=. instead of --cov=src)
- Global storage caching issue in test isolation

### Changed
- Test coverage improved from ~20% to 43%

## [0.3.2] - 2025-01-04

### Fixed
- Timezone handling bug in timestamp formatting

## [0.3.1] - 2025-01-04

### Fixed
- PyPI package description now properly includes README content

## [0.3.0] - 2025-01-04

### Added
- **Configuration system**: `~/.workshop/config.json` for per-project database management
- Web UI settings page for editing configuration
- Platform-specific JSONL import error messages with troubleshooting steps
- Comprehensive documentation in README about JSONL file locations
- Full test suite for config module (24 tests, 98% coverage)
- Full test suite for storage_sqlite module (26 tests)

### Changed
- Per-project databases now auto-register on first use
- Moved README to git root for better visibility
- Enhanced import error messages with platform-specific help

### Fixed
- Compaction summaries now properly imported (were being filtered as noise)

## [0.2.6] - 2025-01-04

### Changed
- AI-analyzed pattern improvements resulting in 3x better extraction quality
- Enhanced extraction patterns based on real conversation analysis

## [0.2.5] - 2025-01-03

### Fixed
- Import now finds JSONL files when .claude/ directory is in parent directory

## [0.2.4] - 2025-01-03

### Fixed
- Workshop now correctly finds project root from any subdirectory

## [0.2.3] - 2025-01-03

### Changed
- Improved JSONL import quality with better noise filtering

## [0.2.2] - 2025-01-03

### Fixed
- Correct JSONL path resolution for projects with underscores in their names

## [0.2.1] - 2025-01-03

### Fixed
- Added missing `display_error` function

## [0.2.0] - 2025-01-03

### Added
- **JSONL Import Feature**: Automatically import conversation history from Claude Code sessions
- Smart extraction of decisions, gotchas, preferences from conversation transcripts
- Compaction summary extraction for preserving context across sessions
- Pattern-based extraction with confidence scoring
- Content deduplication using MD5 hashing

## [0.1.10] - 2025-01-03

### Fixed
- Init command now always updates local Claude Code configuration

## [0.1.9] - 2025-01-03

### Changed
- Updated Claude Code instructions with full command reference

## [0.1.8] - 2025-01-03

### Added
- Delete command for removing entries
- Cleanup command for database maintenance

## [0.1.7] - 2025-01-03

### Fixed
- Template file packaging in distribution

## [0.1.6] - 2025-01-03

### Changed
- Init command now updates Workshop instructions in Claude Code

## [0.1.5] - 2025-01-03

### Changed
- Updated Claude Code instructions for goal management workflow

## [0.1.4] - 2025-01-03

### Added
- Goal completion commands (`workshop next done`, `workshop next skip`)
- Enhanced goal tracking workflow

## [0.1.3] - 2025-01-03

### Added
- Export command for web chat continuity
- Ability to export Workshop context for use in Claude.ai web interface

## [0.1.2] - 2025-01-03

### Added
- PreCompact hook to preserve context before compaction
- Automatic context preservation during Claude Code session compaction

## [0.1.1] - 2025-01-03

### Changed
- README clarification: Workshop is a tool FOR Claude, not just about Claude
- Improved messaging about Workshop's purpose

## [0.1.0] - 2025-01-03

### Added
- Initial PyPI release
- Core Workshop functionality:
  - Session-aware context tracking
  - Entry types: decisions, notes, gotchas, preferences, goals, blockers, next steps
  - Full-text search with FTS5
  - Tag and file association support
  - Git integration
  - Rich terminal UI with emoji indicators
  - Session start/end hooks for Claude Code
  - Web admin interface (optional)
- SQLite storage with schema migrations
- CLI with commands: note, decision, gotcha, preference, goal, blocker, next, search, context, recent
- Timestamp formatting (relative and absolute)

[1.0.5]: https://github.com/zachswift615/workshop/compare/v1.0.4...v1.0.5
[1.0.4]: https://github.com/zachswift615/workshop/compare/v1.0.3...v1.0.4
[1.0.3]: https://github.com/zachswift615/workshop/compare/v1.0.2...v1.0.3
[1.0.2]: https://github.com/zachswift615/workshop/compare/v1.0.1...v1.0.2
[1.0.1]: https://github.com/zachswift615/workshop/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/zachswift615/workshop/compare/v0.3.4...v1.0.0
[0.3.4]: https://github.com/zachswift615/workshop/compare/v0.3.0...v0.3.4
[0.3.3]: https://github.com/zachswift615/workshop/compare/v0.3.0...v0.3.3
[0.3.2]: https://github.com/zachswift615/workshop/compare/v0.3.1...v0.3.2
[0.3.1]: https://github.com/zachswift615/workshop/compare/v0.3.0...v0.3.1
[0.3.0]: https://github.com/zachswift615/workshop/compare/v0.2.6...v0.3.0
[0.2.6]: https://github.com/zachswift615/workshop/compare/v0.2.5...v0.2.6
[0.2.5]: https://github.com/zachswift615/workshop/compare/v0.2.4...v0.2.5
[0.2.4]: https://github.com/zachswift615/workshop/compare/v0.2.3...v0.2.4
[0.2.3]: https://github.com/zachswift615/workshop/compare/v0.2.2...v0.2.3
[0.2.2]: https://github.com/zachswift615/workshop/compare/v0.2.1...v0.2.2
[0.2.1]: https://github.com/zachswift615/workshop/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/zachswift615/workshop/compare/v0.1.10...v0.2.0
[0.1.10]: https://github.com/zachswift615/workshop/compare/v0.1.9...v0.1.10
[0.1.9]: https://github.com/zachswift615/workshop/compare/v0.1.8...v0.1.9
[0.1.8]: https://github.com/zachswift615/workshop/compare/v0.1.7...v0.1.8
[0.1.7]: https://github.com/zachswift615/workshop/compare/v0.1.6...v0.1.7
[0.1.6]: https://github.com/zachswift615/workshop/compare/v0.1.5...v0.1.6
[0.1.5]: https://github.com/zachswift615/workshop/compare/v0.1.4...v0.1.5
[0.1.4]: https://github.com/zachswift615/workshop/compare/v0.1.3...v0.1.4
[0.1.3]: https://github.com/zachswift615/workshop/compare/v0.1.2...v0.1.3
[0.1.2]: https://github.com/zachswift615/workshop/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/zachswift615/workshop/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/zachswift615/workshop/releases/tag/v0.1.0
[1.0.6]: https://github.com/zachswift615/workshop/compare/v1.0.5...v1.0.6
[1.1.0]: https://github.com/zachswift615/workshop/compare/v1.0.6...v1.1.0
[2.0.0]: https://github.com/zachswift615/workshop/compare/v1.1.0...v2.0.0
[2.0.1]: https://github.com/zachswift615/workshop/compare/v2.0.0...v2.0.1
[2.0.2]: https://github.com/zachswift615/workshop/compare/v2.0.1...v2.0.2
[2.0.3]: https://github.com/zachswift615/workshop/compare/v2.0.2...v2.0.3
[2.1.0]: https://github.com/zachswift615/workshop/compare/v2.0.3...v2.1.0
[2.2.0]: https://github.com/zachswift615/workshop/compare/v2.1.0...v2.2.0
[2.2.1]: https://github.com/zachswift615/workshop/compare/v2.2.0...v2.2.1
[2.2.2]: https://github.com/zachswift615/workshop/compare/v2.2.1...v2.2.2
[2.2.3]: https://github.com/zachswift615/workshop/compare/v2.2.2...v2.2.3
[2.2.4]: https://github.com/zachswift615/workshop/compare/v2.2.3...v2.2.4
[2.2.5]: https://github.com/zachswift615/workshop/compare/v2.2.4...v2.2.5
[2.2.6]: https://github.com/zachswift615/workshop/compare/v2.2.5...v2.2.6
[2.2.7]: https://github.com/zachswift615/workshop/compare/v2.2.6...v2.2.7
[2.2.8]: https://github.com/zachswift615/workshop/compare/v2.2.7...v2.2.8
[2.2.9]: https://github.com/zachswift615/workshop/compare/v2.2.8...v2.2.9
[2.3.0]: https://github.com/zachswift615/workshop/compare/v2.2.9...v2.3.0
[2.3.1]: https://github.com/zachswift615/workshop/compare/v2.3.0...v2.3.1
[2.3.2]: https://github.com/zachswift615/workshop/compare/v2.3.1...v2.3.2
[2.4.0]: https://github.com/zachswift615/workshop/compare/v2.3.2...v2.4.0
[2.4.1]: https://github.com/zachswift615/workshop/compare/v2.4.0...v2.4.1
[2.4.2]: https://github.com/zachswift615/workshop/compare/v2.4.1...v2.4.2
[2.5.0]: https://github.com/zachswift615/workshop/compare/v2.4.2...v2.5.0
[2.6.0]: https://github.com/zachswift615/workshop/compare/v2.5.0...v2.6.0
[2.7.0]: https://github.com/zachswift615/workshop/compare/v2.6.0...v2.7.0
[2.8.0]: https://github.com/zachswift615/workshop/compare/v2.7.0...v2.8.0
