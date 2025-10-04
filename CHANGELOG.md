# Changelog

All notable changes to Workshop will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
