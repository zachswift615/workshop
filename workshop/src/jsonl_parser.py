"""
JSONL Parser for Workshop - Extract knowledge from Claude Code session transcripts
"""
import json
import re
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass


@dataclass
class ExtractedEntry:
    """Represents an extracted entry from JSONL"""
    type: str  # decision, gotcha, note, preference
    content: str
    reasoning: Optional[str] = None
    confidence: float = 1.0
    timestamp: str = ""
    source_uuid: str = ""


@dataclass
class SessionImportResult:
    """Result of importing a JSONL session"""
    jsonl_path: str
    session_summary: str
    entries: List[ExtractedEntry]
    last_message_uuid: str
    last_message_timestamp: str
    messages_processed: int


class JSONLParser:
    """Parse Claude Code JSONL session transcripts"""

    # Keywords for pattern extraction
    DECISION_KEYWORDS = [
        r'decided to',
        r'chose to',
        r'went with',
        r'using .* because',
        r'opted for',
        r'settled on',
    ]

    GOTCHA_KEYWORDS = [
        r'watch out for',
        r'gotcha',
        r'be careful',
        r'tricky',
        r'important to note',
        r'constraint',
        r'limitation',
        r'failed because',
        r'error:',
        r'doesn\'t work',
    ]

    PREFERENCE_KEYWORDS = [
        r'prefer',
        r'always use',
        r'typically',
        r'usually',
        r'style:',
    ]

    def __init__(self):
        self.decision_pattern = re.compile('|'.join(self.DECISION_KEYWORDS), re.IGNORECASE)
        self.gotcha_pattern = re.compile('|'.join(self.GOTCHA_KEYWORDS), re.IGNORECASE)
        self.preference_pattern = re.compile('|'.join(self.PREFERENCE_KEYWORDS), re.IGNORECASE)

    def parse_jsonl_file(
        self,
        jsonl_path: Path,
        start_from_uuid: Optional[str] = None
    ) -> SessionImportResult:
        """
        Parse a JSONL file and extract workshop entries.

        Args:
            jsonl_path: Path to JSONL file
            start_from_uuid: If provided, only process messages after this UUID

        Returns:
            SessionImportResult with extracted entries
        """
        messages = self._read_jsonl(jsonl_path)

        if not messages:
            return SessionImportResult(
                jsonl_path=str(jsonl_path),
                session_summary="",
                entries=[],
                last_message_uuid="",
                last_message_timestamp="",
                messages_processed=0
            )

        # Filter messages if starting from UUID
        if start_from_uuid:
            messages = self._filter_from_uuid(messages, start_from_uuid)

        # Extract session summary
        session_summary = self._extract_session_summary(messages)

        # Extract entries from messages
        entries = []
        for msg in messages:
            msg_entries = self._extract_from_message(msg)
            entries.extend(msg_entries)

        # Get last message info
        last_msg = messages[-1] if messages else {}
        last_uuid = last_msg.get('uuid', '')
        last_timestamp = last_msg.get('timestamp', '')

        return SessionImportResult(
            jsonl_path=str(jsonl_path),
            session_summary=session_summary,
            entries=entries,
            last_message_uuid=last_uuid,
            last_message_timestamp=last_timestamp,
            messages_processed=len(messages)
        )

    def _read_jsonl(self, jsonl_path: Path) -> List[Dict]:
        """
        Read JSONL file safely (read-only).

        Args:
            jsonl_path: Path to JSONL file

        Returns:
            List of message dictionaries
        """
        messages = []

        try:
            with open(jsonl_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue

                    try:
                        msg = json.loads(line)
                        messages.append(msg)
                    except json.JSONDecodeError as e:
                        # Skip corrupted lines gracefully
                        print(f"Warning: Skipping corrupted line {line_num} in {jsonl_path.name}: {e}")
                        continue

        except Exception as e:
            print(f"Error reading {jsonl_path}: {e}")
            return []

        return messages

    def _filter_from_uuid(self, messages: List[Dict], start_uuid: str) -> List[Dict]:
        """Filter messages starting after a specific UUID"""
        found = False
        filtered = []

        for msg in messages:
            if found:
                filtered.append(msg)
            elif msg.get('uuid') == start_uuid:
                found = True  # Start collecting from NEXT message

        return filtered

    def _extract_session_summary(self, messages: List[Dict]) -> str:
        """Extract session summary from messages"""
        for msg in messages:
            if msg.get('type') == 'summary' and msg.get('summary'):
                return msg['summary']
        return ""

    def _extract_from_message(self, message: Dict) -> List[ExtractedEntry]:
        """
        Extract workshop entries from a single message.

        Args:
            message: JSONL message dictionary

        Returns:
            List of extracted entries
        """
        entries = []

        # Only extract from user and assistant messages
        msg_type = message.get('type')
        if msg_type not in ['user', 'assistant']:
            return entries

        # Get message content
        content = self._get_message_content(message)
        if not content:
            return entries

        timestamp = message.get('timestamp', datetime.now().isoformat())
        uuid = message.get('uuid', '')

        # Extract decisions
        decisions = self._extract_decisions(content, timestamp, uuid)
        entries.extend(decisions)

        # Extract gotchas
        gotchas = self._extract_gotchas(content, timestamp, uuid)
        entries.extend(gotchas)

        # Extract preferences (from user messages only)
        if msg_type == 'user':
            preferences = self._extract_preferences(content, timestamp, uuid)
            entries.extend(preferences)

        # Extract tool errors
        if msg_type == 'user' and 'tool_use_id' in message.get('message', {}).get('content', [{}])[0]:
            tool_errors = self._extract_tool_errors(message, timestamp, uuid)
            entries.extend(tool_errors)

        return entries

    def _get_message_content(self, message: Dict) -> str:
        """Extract text content from message, filtering out system messages"""
        msg_data = message.get('message', {})

        if isinstance(msg_data, dict):
            content_parts = msg_data.get('content', [])

            if isinstance(content_parts, str):
                content = content_parts
            elif isinstance(content_parts, list):
                texts = []
                for part in content_parts:
                    if isinstance(part, dict):
                        # Skip tool results and system messages
                        if part.get('type') in ['tool_result', 'tool_use']:
                            continue
                        if part.get('type') == 'text':
                            texts.append(part.get('text', ''))
                    elif isinstance(part, str):
                        texts.append(part)
                content = ' '.join(texts)
            else:
                return ""

            # Filter out obvious noise
            if self._is_noise(content):
                return ""

            return content

        return ""

    def _is_noise(self, content: str) -> bool:
        """Check if content is likely noise (hooks, JSON, etc.)"""
        if not content or len(content) < 20:
            return True

        # Skip if it looks like JSON
        if content.strip().startswith(('{', '[', '"role":', '"message":')):
            return True

        # Skip if it's mostly code/markup
        code_indicators = ['```', '```python', '```javascript', 'def ', 'function ', 'class ', 'import ']
        if any(indicator in content for indicator in code_indicators):
            return True

        # Skip session hooks
        if 'session-start-hook' in content or 'session-end-hook' in content:
            return True

        # Skip if it's just an error message fragment
        if content.startswith(('Error:', 'Traceback', 'AttributeError:', 'KeyError:', 'TypeError:')):
            return True

        return False

    def _extract_decisions(
        self,
        content: str,
        timestamp: str,
        uuid: str
    ) -> List[ExtractedEntry]:
        """Extract decisions from content using pattern matching"""
        decisions = []

        # Look for decision patterns
        for match in self.decision_pattern.finditer(content):
            # Extract sentence containing the decision
            sentence = self._extract_sentence_around_match(content, match)

            if not sentence or len(sentence) < 20:
                continue

            # Skip if sentence looks like noise
            if self._is_low_quality_sentence(sentence):
                continue

            # Try to extract reasoning
            reasoning = self._extract_reasoning(content, match)

            decisions.append(ExtractedEntry(
                type='decision',
                content=sentence,
                reasoning=reasoning,
                confidence=0.7,  # Medium confidence for pattern matching
                timestamp=timestamp,
                source_uuid=uuid
            ))

        return decisions

    def _extract_gotchas(
        self,
        content: str,
        timestamp: str,
        uuid: str
    ) -> List[ExtractedEntry]:
        """Extract gotchas from content"""
        gotchas = []

        for match in self.gotcha_pattern.finditer(content):
            sentence = self._extract_sentence_around_match(content, match)

            if not sentence or len(sentence) < 15:
                continue

            # Skip if sentence looks like noise
            if self._is_low_quality_sentence(sentence):
                continue

            gotchas.append(ExtractedEntry(
                type='gotcha',
                content=sentence,
                confidence=0.8,
                timestamp=timestamp,
                source_uuid=uuid
            ))

        return gotchas

    def _extract_preferences(
        self,
        content: str,
        timestamp: str,
        uuid: str
    ) -> List[ExtractedEntry]:
        """Extract user preferences from content"""
        preferences = []

        for match in self.preference_pattern.finditer(content):
            sentence = self._extract_sentence_around_match(content, match)

            if not sentence or len(sentence) < 15:
                continue

            # Skip if sentence looks like noise
            if self._is_low_quality_sentence(sentence):
                continue

            preferences.append(ExtractedEntry(
                type='preference',
                content=sentence,
                confidence=0.6,
                timestamp=timestamp,
                source_uuid=uuid
            ))

        return preferences

    def _extract_tool_errors(
        self,
        message: Dict,
        timestamp: str,
        uuid: str
    ) -> List[ExtractedEntry]:
        """Extract gotchas from tool errors"""
        entries = []

        msg_data = message.get('message', {})
        content_parts = msg_data.get('content', [])

        for part in content_parts:
            if isinstance(part, dict) and part.get('type') == 'tool_result':
                if part.get('is_error'):
                    error_content = part.get('content', '')
                    if error_content:
                        entries.append(ExtractedEntry(
                            type='gotcha',
                            content=f"Tool error: {error_content[:200]}",
                            confidence=0.9,  # High confidence for actual errors
                            timestamp=timestamp,
                            source_uuid=uuid
                        ))

        return entries

    def _is_low_quality_sentence(self, sentence: str) -> bool:
        """Check if a sentence is likely low quality/noise"""
        # Too short or too long
        if len(sentence) < 20 or len(sentence) > 500:
            return True

        # Contains mostly special characters
        special_char_ratio = sum(1 for c in sentence if not c.isalnum() and c != ' ') / len(sentence)
        if special_char_ratio > 0.3:
            return True

        # Starts with command/code patterns
        if sentence.strip().startswith(('$', '>', 'npm ', 'cd ', 'ls ', 'git ', 'workshop ')):
            return True

        # Contains JSON-like patterns
        if '{' in sentence and '}' in sentence and '"' in sentence:
            return True

        # Contains newline escapes (suggests it's from JSON)
        if '\\n' in sentence or '\\t' in sentence:
            return True

        # Incomplete sentence (no verb/subject structure)
        words = sentence.split()
        if len(words) < 4:
            return True

        return False

    def _extract_sentence_around_match(self, text: str, match: re.Match) -> str:
        """Extract the sentence containing a regex match"""
        # Find sentence boundaries
        start = text.rfind('.', 0, match.start()) + 1
        end = text.find('.', match.end())

        if end == -1:
            end = len(text)

        sentence = text[start:end].strip()
        return sentence

    def _extract_reasoning(self, content: str, match: re.Match) -> Optional[str]:
        """Try to extract reasoning after a decision"""
        # Look for "because" after the match
        after_match = content[match.end():match.end() + 200]

        because_patterns = [r'because', r'since', r'as', r'to']

        for pattern in because_patterns:
            if re.search(pattern, after_match, re.IGNORECASE):
                # Extract up to next period
                end = after_match.find('.')
                if end != -1:
                    reasoning = after_match[:end].strip()
                    if len(reasoning) > 10:
                        return reasoning

        return None

    def calculate_file_hash(self, jsonl_path: Path) -> str:
        """Calculate SHA256 hash of JSONL file"""
        sha256 = hashlib.sha256()

        with open(jsonl_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                sha256.update(chunk)

        return sha256.hexdigest()
