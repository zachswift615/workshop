"""
JSONL Parser for Workshop - Extract knowledge from Claude Code session transcripts
"""
import json
import re
import hashlib
import os
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
        # Enhanced patterns from analysis
        r'caveat:',
        r'won\'t work (?:if|when)',
        r'only works (?:if|when)',
        r'must (?:be|have)',
        r'requires? that',
        r'make sure to',
        r'don\'t forget to',
    ]

    PREFERENCE_KEYWORDS = [
        r'prefer',
        r'always use',
        r'typically',
        r'usually',
        r'style:',
    ]

    def __init__(self, api_key: Optional[str] = None, llm_endpoint: Optional[str] = None):
        self.decision_pattern = re.compile('|'.join(self.DECISION_KEYWORDS), re.IGNORECASE)
        self.gotcha_pattern = re.compile('|'.join(self.GOTCHA_KEYWORDS), re.IGNORECASE)
        self.preference_pattern = re.compile('|'.join(self.PREFERENCE_KEYWORDS), re.IGNORECASE)

        # LLM support
        self.anthropic_client = None
        self.openai_client = None
        self.llm_type = None

        # Local LM Studio endpoint
        if llm_endpoint:
            try:
                import openai
                self.openai_client = openai.OpenAI(
                    base_url=llm_endpoint,
                    api_key="not-needed"  # LM Studio doesn't require API key
                )
                self.llm_type = 'local'
            except ImportError:
                pass
        # Anthropic API
        elif api_key or os.getenv('ANTHROPIC_API_KEY'):
            try:
                import anthropic
                self.anthropic_client = anthropic.Anthropic(api_key=api_key or os.getenv('ANTHROPIC_API_KEY'))
                self.llm_type = 'anthropic'
            except ImportError:
                pass  # LLM features not available without anthropic package

    @staticmethod
    def check_local_llm_server(endpoint: str = "http://localhost:1234") -> bool:
        """Check if local LLM server (like LM Studio) is running"""
        try:
            import requests
            response = requests.get(f"{endpoint}/v1/models", timeout=2)
            return response.status_code == 200
        except:
            return False

    def parse_jsonl_file(
        self,
        jsonl_path: Path,
        start_from_uuid: Optional[str] = None,
        use_llm: bool = False
    ) -> SessionImportResult:
        """
        Parse a JSONL file and extract workshop entries.

        Args:
            jsonl_path: Path to JSONL file
            start_from_uuid: If provided, only process messages after this UUID
            use_llm: If True, use LLM extraction instead of pattern matching

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

        # Extract entries from messages with deduplication
        entries = []
        seen_content_hashes = set()

        # Choose extraction method
        extract_fn = self._extract_from_message_llm if use_llm else self._extract_from_message

        for msg in messages:
            msg_entries = extract_fn(msg)

            # Deduplicate by content hash
            for entry in msg_entries:
                content_hash = hashlib.md5(entry.content.encode('utf-8')).hexdigest()
                if content_hash not in seen_content_hashes:
                    seen_content_hashes.add(content_hash)
                    entries.append(entry)

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

    def _extract_summary_sections(self, content: str, timestamp: str, uuid: str) -> List[ExtractedEntry]:
        """Extract ## Summary sections from assistant messages"""
        entries = []

        # Find summary sections
        summary_pattern = re.compile(
            r'##+ Summary.*?(?=\n##|$)',
            re.IGNORECASE | re.DOTALL
        )

        for match in summary_pattern.finditer(content):
            summary_text = match.group(0).strip()

            # Skip if too short (likely not a real summary)
            if len(summary_text) < 100:
                continue

            entries.append(ExtractedEntry(
                type='note',
                content=summary_text,
                confidence=0.9,  # High confidence - explicitly marked
                timestamp=timestamp,
                source_uuid=uuid
            ))

        return entries

    def _extract_completion_summaries(self, content: str, timestamp: str, uuid: str) -> List[ExtractedEntry]:
        """Extract completion summaries with numbered lists"""
        entries = []

        # Pattern 1: "Perfect/Great/Done! I've:" followed by content
        completion_pattern_1 = re.compile(
            r'(?:Perfect|Great|Done|Excellent)!\s+I\'ve:\s*\n\n(?:.*?)(?=\n\n\n|\n\n##|$)',
            re.IGNORECASE | re.DOTALL
        )

        # Pattern 2: "X is now working! The issue was... The solution includes:"
        completion_pattern_2 = re.compile(
            r'(?:.*?)\s+is now working!\s+The issue was.*?The solution includes:\s*\n(?:.*?)(?=\n\n\n|\n\n##|$)',
            re.IGNORECASE | re.DOTALL
        )

        # Pattern 3: "Perfect/Great! Now X will:" followed by numbered list
        completion_pattern_3 = re.compile(
            r'(?:Perfect|Great|Done|Excellent)!\s+Now\s+.*?:\s*\n(?:.*?)(?=\n\n\n|\n\n##|$)',
            re.IGNORECASE | re.DOTALL
        )

        for pattern in [completion_pattern_1, completion_pattern_2, completion_pattern_3]:
            for match in pattern.finditer(content):
                completion_text = match.group(0).strip()

                # Must contain at least 2 numbered items to be valid
                numbered_items = re.findall(r'^\d+\.', completion_text, re.MULTILINE)
                if len(numbered_items) < 2:
                    continue

                # Skip if too short
                if len(completion_text) < 100:
                    continue

                entries.append(ExtractedEntry(
                    type='note',
                    content=completion_text,
                    confidence=0.95,  # Very high confidence - clear completion summary
                    timestamp=timestamp,
                    source_uuid=uuid
                ))

        return entries

    def _extract_problem_solutions(self, content: str, timestamp: str, uuid: str) -> List[ExtractedEntry]:
        """Extract problem/solution pairs and root causes"""
        entries = []

        # Pattern for "Fixed!" sections
        fixed_pattern = re.compile(
            r'##+ (?:Fixed|Resolved|Complete|Done)!?.*?(?=\n##|$)',
            re.IGNORECASE | re.DOTALL
        )

        for match in fixed_pattern.finditer(content):
            fixed_text = match.group(0).strip()
            if len(fixed_text) > 50:  # Skip very short ones
                entries.append(ExtractedEntry(
                    type='note',
                    content=fixed_text,
                    confidence=0.9,
                    timestamp=timestamp,
                    source_uuid=uuid
                ))

        # Pattern for root cause explanations
        root_cause_pattern = re.compile(
            r'[Tt]he (?:problem|issue|bug) was that .+?\.',
            re.DOTALL
        )

        for match in root_cause_pattern.finditer(content):
            sentence = match.group(0).strip()
            if len(sentence) > 30 and len(sentence) < 500:
                entries.append(ExtractedEntry(
                    type='gotcha',
                    content=sentence,
                    confidence=0.85,
                    timestamp=timestamp,
                    source_uuid=uuid
                ))

        return entries

    def _extract_discoveries(self, content: str, timestamp: str, uuid: str) -> List[ExtractedEntry]:
        """Extract technical discoveries and realizations"""
        entries = []

        discovery_patterns = [
            r'[Dd]iscovered that .+?\.',
            r'[Ff]ound that .+?\.',
            r'[Rr]ealized that .+?\.',
            r'[Tt]urns out .+?\.',
            r'[Ii]mportant to note that .+?\.',
        ]

        pattern = re.compile('|'.join(discovery_patterns))

        for match in pattern.finditer(content):
            sentence = match.group(0).strip()
            if len(sentence) > 20 and len(sentence) < 300 and not self._is_low_quality_sentence(sentence):
                entries.append(ExtractedEntry(
                    type='gotcha',
                    content=sentence,
                    confidence=0.8,
                    timestamp=timestamp,
                    source_uuid=uuid
                ))

        return entries

    def _extract_compaction_summary(self, content: str, timestamp: str, uuid: str) -> List[ExtractedEntry]:
        """Extract post-compaction conversation summaries"""
        entries = []

        # Look for the characteristic pattern of compaction summaries
        if "This session is being continued from a previous conversation that ran out of context" in content:
            # Extract the entire summary starting after "Analysis:"
            analysis_match = re.search(r'Analysis:\s*(.*)', content, re.DOTALL)
            if analysis_match:
                summary_content = analysis_match.group(1).strip()

                # Only extract if it's substantial (compaction summaries are usually very long)
                if len(summary_content) > 500:
                    entries.append(ExtractedEntry(
                        type='note',
                        content=f"# Session Continuation Summary\n\n{summary_content}",
                        confidence=1.0,  # These are comprehensive summaries
                        timestamp=timestamp,
                        source_uuid=uuid
                    ))

        return entries

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

        timestamp = message.get('timestamp', datetime.now().isoformat())
        uuid = message.get('uuid', '')

        # IMPORTANT: Extract tool errors FIRST (before content check)
        # Tool error messages may not have normal content
        if msg_type == 'user' and 'tool_use_id' in message.get('message', {}).get('content', [{}])[0]:
            tool_errors = self._extract_tool_errors(message, timestamp, uuid)
            entries.extend(tool_errors)

        # Get message content
        content = self._get_message_content(message)
        if not content:
            return entries

        # NEW: Extract compaction summaries (user messages only - these are system-generated)
        if msg_type == 'user':
            compaction = self._extract_compaction_summary(content, timestamp, uuid)
            entries.extend(compaction)

        # NEW: Extract summary sections (assistant only)
        if msg_type == 'assistant':
            summaries = self._extract_summary_sections(content, timestamp, uuid)
            entries.extend(summaries)

        # NEW: Extract completion summaries (assistant only)
        if msg_type == 'assistant':
            completions = self._extract_completion_summaries(content, timestamp, uuid)
            entries.extend(completions)

        # NEW: Extract problem/solution pairs (assistant only)
        if msg_type == 'assistant':
            solutions = self._extract_problem_solutions(content, timestamp, uuid)
            entries.extend(solutions)

        # NEW: Extract discoveries (assistant only)
        if msg_type == 'assistant':
            discoveries = self._extract_discoveries(content, timestamp, uuid)
            entries.extend(discoveries)

        # EXISTING: Extract decisions
        decisions = self._extract_decisions(content, timestamp, uuid)
        entries.extend(decisions)

        # EXISTING: Extract gotchas
        gotchas = self._extract_gotchas(content, timestamp, uuid)
        entries.extend(gotchas)

        # EXISTING: Extract preferences (from user messages only)
        if msg_type == 'user':
            preferences = self._extract_preferences(content, timestamp, uuid)
            entries.extend(preferences)

        return entries

    def _extract_from_message_llm(self, message: Dict) -> List[ExtractedEntry]:
        """
        Extract workshop entries from a message using LLM analysis.
        Supports both Anthropic API and local LLM servers (LM Studio).

        Args:
            message: JSONL message dictionary

        Returns:
            List of extracted entries with high-quality reasoning
        """
        if not self.anthropic_client and not self.openai_client:
            # Fallback to pattern matching if no LLM available
            return self._extract_from_message(message)

        entries = []

        # Only extract from user and assistant messages
        msg_type = message.get('type')
        if msg_type not in ['user', 'assistant']:
            return entries

        timestamp = message.get('timestamp', datetime.now().isoformat())
        uuid = message.get('uuid', '')

        # Get message content
        content = self._get_message_content(message)
        if not content or len(content) < 50:  # Skip very short messages
            return entries

        # Build LLM prompt for extraction
        prompt = f"""Analyze this conversation message from a Claude Code session and extract structured insights.

Message: {content}

Extract the following types of information:

1. **Decisions**: Technical or architectural decisions that were made
   - Include what was decided
   - Include WHY it was decided (reasoning, trade-offs)
   - Include alternatives considered if mentioned

2. **Gotchas/Constraints**: Problems, bugs, or important constraints discovered
   - What the issue/constraint is
   - Why it matters or how it was discovered

3. **Preferences**: User's stated preferences or patterns
   - What the preference is
   - Any reasoning given

Return ONLY valid JSON in this exact format:
{{
  "decisions": [
    {{"content": "brief decision", "reasoning": "detailed explanation including why, trade-offs, alternatives"}},
  ],
  "gotchas": [
    {{"content": "the gotcha/constraint", "reasoning": "why this matters or context"}},
  ],
  "preferences": [
    {{"content": "the preference", "reasoning": "any explanation given"}},
  ]
}}

If a category has no entries, use an empty array. Do NOT include any text outside the JSON object."""

        try:
            # Call appropriate LLM API
            if self.llm_type == 'anthropic':
                # Anthropic API (Claude Haiku)
                response = self.anthropic_client.messages.create(
                    model="claude-3-haiku-20240307",
                    max_tokens=2000,
                    messages=[{"role": "user", "content": prompt}]
                )
                llm_text = response.content[0].text.strip()
            elif self.llm_type == 'local':
                # OpenAI-compatible API (LM Studio)
                response = self.openai_client.chat.completions.create(
                    model="local-model",  # LM Studio uses whatever model is loaded
                    max_tokens=2000,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.7
                )
                llm_text = response.choices[0].message.content.strip()
            else:
                # No client available
                return self._extract_from_message(message)

            # Extract JSON from response (in case LLM adds surrounding text)
            json_match = re.search(r'\{[\s\S]*\}', llm_text)
            if not json_match:
                # No JSON found in response, fall back to pattern matching
                print("LLM response contained no JSON, falling back to pattern matching")
                return self._extract_from_message(message)

            llm_json = json.loads(json_match.group())

            # Create entries from LLM extraction
            for decision in llm_json.get('decisions', []):
                if decision.get('content'):
                    entries.append(ExtractedEntry(
                        type='decision',
                        content=decision['content'],
                        reasoning=decision.get('reasoning'),
                        confidence=0.95,  # High confidence for LLM extraction
                        timestamp=timestamp,
                        source_uuid=uuid
                    ))

            for gotcha in llm_json.get('gotchas', []):
                if gotcha.get('content'):
                    entries.append(ExtractedEntry(
                        type='gotcha',
                        content=gotcha['content'],
                        reasoning=gotcha.get('reasoning'),
                        confidence=0.95,
                        timestamp=timestamp,
                        source_uuid=uuid
                    ))

            for pref in llm_json.get('preferences', []):
                if pref.get('content'):
                    entries.append(ExtractedEntry(
                        type='preference',
                        content=pref['content'],
                        reasoning=pref.get('reasoning'),
                        confidence=0.95,
                        timestamp=timestamp,
                        source_uuid=uuid
                    ))

        except Exception as e:
            # If LLM extraction fails, fallback to pattern matching
            print(f"LLM extraction failed: {e}, falling back to pattern matching")
            return self._extract_from_message(message)

        return entries

    def _get_message_content(self, message: Dict, skip_noise_filter: bool = False) -> str:
        """
        Extract text content from message, filtering out system messages.

        Args:
            message: Message dictionary from JSONL
            skip_noise_filter: If True, skip noise filtering (for raw message storage)

        Returns:
            Extracted text content
        """
        # Handle system messages (type: "system" with top-level content)
        if message.get('type') == 'system':
            content = message.get('content', '')
            if isinstance(content, str):
                if not skip_noise_filter and self._is_noise(content):
                    return ""
                return content

        msg_data = message.get('message', {})

        if isinstance(msg_data, dict):
            content_parts = msg_data.get('content', [])

            if isinstance(content_parts, str):
                content = content_parts
            elif isinstance(content_parts, list):
                texts = []
                for part in content_parts:
                    if isinstance(part, dict):
                        # Skip tool results and tool uses
                        if part.get('type') in ['tool_result', 'tool_use']:
                            continue
                        # Handle text content
                        if part.get('type') == 'text':
                            texts.append(part.get('text', ''))
                        # Handle thinking content
                        elif part.get('type') == 'thinking':
                            texts.append(part.get('thinking', ''))
                    elif isinstance(part, str):
                        texts.append(part)
                content = ' '.join(texts)
            else:
                return ""

            # Filter out obvious noise (unless we're storing raw messages)
            if not skip_noise_filter and self._is_noise(content):
                return ""

            return content

        return ""

    def _is_noise(self, content: str) -> bool:
        """Check if content is likely noise (hooks, JSON, etc.)"""
        if not content or len(content) < 20:
            return True

        # EXCEPTION: Always allow compaction summaries through
        if "This session is being continued from a previous conversation" in content:
            return False

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
