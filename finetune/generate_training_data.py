#!/usr/bin/env python3
"""
Generate fine-tuning training data from ANY codebase.
Uses Claude API OR local LM Studio to auto-generate Q&A pairs from your code.
Optionally includes workshop entries if available.

Usage:
    # With Claude API (fast, $0.50-2 cost)
    python generate_training_data.py --project "MyProject" --src ../src --api-key $ANTHROPIC_API_KEY

    # With LM Studio (free, slower, can run overnight)
    python generate_training_data.py --project "MyProject" --src ../src --lm-studio http://localhost:1234/v1
"""
import json
import argparse
from pathlib import Path
import sqlite3
import time


class LLMClient:
    """Unified interface for Claude API or LM Studio."""

    def __init__(self, backend="claude", api_key=None, base_url=None):
        self.backend = backend

        if backend == "claude":
            from anthropic import Anthropic

            self.client = Anthropic(api_key=api_key)
            self.model = "claude-3-5-sonnet-20241022"
        elif backend == "lm-studio":
            from openai import OpenAI

            self.client = OpenAI(
                base_url=base_url or "http://localhost:1234/v1", api_key="lm-studio"  # LM Studio doesn't need real key
            )
            # LM Studio uses whatever model is loaded
            self.model = "local-model"
        else:
            raise ValueError(f"Unknown backend: {backend}")

    def generate(self, prompt, max_tokens=2000):
        """Generate completion (works with both backends)."""
        if self.backend == "claude":
            response = self.client.messages.create(
                model=self.model, max_tokens=max_tokens, messages=[{"role": "user", "content": prompt}]
            )
            return response.content[0].text

        elif self.backend == "lm-studio":
            response = self.client.chat.completions.create(
                model=self.model, messages=[{"role": "user", "content": prompt}], max_tokens=max_tokens, temperature=0.7
            )
            return response.choices[0].message.content


def save_progress(output_file, examples):
    """Save progress to allow resuming if interrupted."""
    progress_file = Path(output_file).with_suffix(".progress.jsonl")
    with open(progress_file, "w") as f:
        for item in examples:
            f.write(json.dumps(item) + "\n")


def load_progress(output_file):
    """Load previously saved progress."""
    progress_file = Path(output_file).with_suffix(".progress.jsonl")
    if not progress_file.exists():
        return []

    examples = []
    with open(progress_file) as f:
        for line in f:
            examples.append(json.loads(line))
    return examples


def analyze_code_file(client, file_path, project_name, max_examples=3, retry_count=3):
    """Use LLM to generate Q&A pairs from a code file."""
    for attempt in range(retry_count):
        try:
            code = file_path.read_text()

            # Skip if file is too short or looks like a config file
            if len(code) < 200 or file_path.name in ["__init__.py", "setup.py", "conftest.py"]:
                return []

            prompt = f"""Analyze this code from the {project_name} project and generate {max_examples} \
high-quality question/answer pairs.

File: {file_path.name}
Code:
```
{code[:4000]}  # Limit to avoid token limits
```

Generate questions that would help someone understand:
- What this code does
- How to use it
- Why it's designed this way
- Common patterns or gotchas

Format as JSON array:
[
  {{
    "question": "What does X do?",
    "context": "Brief context about the file/module",
    "answer": "Detailed explanation"
  }}
]

Only return the JSON array, nothing else."""

            content = client.generate(prompt, max_tokens=2000)

            # Parse JSON from response
            content = content.strip()
            # Remove markdown code blocks if present
            if content.startswith("```"):
                content = content.split("\n", 1)[1]
                content = content.rsplit("\n```", 1)[0]

            qa_pairs = json.loads(content)

            examples = []
            for qa in qa_pairs:
                examples.append(
                    {
                        "instruction": qa["question"],
                        "context": qa.get("context", f"{project_name} - {file_path.name}"),
                        "response": qa["answer"],
                    }
                )

            return examples

        except json.JSONDecodeError:
            if attempt < retry_count - 1:
                print(f"⚠️  JSON error, retrying ({attempt + 1}/{retry_count})...")
                time.sleep(1)
            else:
                print(f"  ⚠️  Failed to parse JSON after {retry_count} attempts: {file_path.name}")
                return []
        except Exception as e:
            if attempt < retry_count - 1:
                print(f"⚠️  Error, retrying ({attempt + 1}/{retry_count}): {e}")
                time.sleep(2)
            else:
                print(f"  ⚠️  Error processing {file_path.name}: {e}")
                return []

    return []


def extract_from_codebase(
    client, src_dirs, project_name, file_patterns, max_files=None, output_file=None, resume=False
):
    """Extract training examples from codebase using LLM."""
    examples = []
    processed_files = set()

    # Load progress if resuming
    if resume and output_file:
        progress_file = Path(output_file).with_suffix(".state.json")
        if progress_file.exists():
            with open(progress_file) as f:
                state = json.load(f)
                processed_files = set(state.get("processed_files", []))
                print(f"  📂 Resuming: {len(processed_files)} files already processed")

    print(f"\n🔍 Analyzing {project_name} codebase...")

    # Collect all matching files
    all_files = []
    for src_dir in src_dirs:
        src_path = Path(src_dir)
        if not src_path.exists():
            print(f"  ⚠️  Directory not found: {src_dir}")
            continue

        for pattern in file_patterns:
            all_files.extend(src_path.glob(pattern))

    # Remove duplicates and sort
    all_files = sorted(set(all_files))

    if max_files:
        all_files = all_files[:max_files]

    # Filter out already processed files
    files_to_process = [f for f in all_files if str(f) not in processed_files]

    print(f"  Found {len(files_to_process)} files to analyze")
    if len(processed_files) > 0:
        print(f"  (Skipping {len(all_files) - len(files_to_process)} already processed)")

    start_time = time.time()

    for i, file_path in enumerate(files_to_process, 1):
        print(f"  [{i}/{len(files_to_process)}] Analyzing {file_path.name}...", end=" ", flush=True)
        file_examples = analyze_code_file(client, file_path, project_name)
        examples.extend(file_examples)
        processed_files.add(str(file_path))
        print(f"✓ {len(file_examples)} examples")

        # Save progress every 5 files
        if output_file and i % 5 == 0:
            save_progress(output_file, examples)
            progress_file = Path(output_file).with_suffix(".state.json")
            with open(progress_file, "w") as f:
                json.dump(
                    {
                        "processed_files": list(processed_files),
                        "total_examples": len(examples),
                        "timestamp": time.time(),
                    },
                    f,
                )

        # Estimate time remaining
        if i % 10 == 0:
            elapsed = time.time() - start_time
            rate = i / elapsed
            remaining = (len(files_to_process) - i) / rate if rate > 0 else 0
            print(f"  ⏱️  Estimated time remaining: {remaining / 60:.1f} minutes")

    return examples


def extract_workshop_entries(db_path, project_name):
    """Extract workshop entries as training examples."""
    examples = []

    if not db_path or not Path(db_path).exists():
        return examples

    print("\n📚 Extracting from Workshop database...")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get decisions with reasoning
    cursor.execute(
        """
        SELECT content, reasoning
        FROM entries
        WHERE type = 'decision' AND reasoning IS NOT NULL
        ORDER BY timestamp DESC
        LIMIT 50
    """
    )

    decisions = cursor.fetchall()
    for content, reasoning in decisions:
        examples.append(
            {
                "instruction": f"Why did we decide to {content.lower()}?",
                "context": f"{project_name} - architectural decision",
                "response": f"Decision: {content}\n\nReasoning: {reasoning}",
            }
        )

    # Get gotchas
    cursor.execute(
        """
        SELECT content, reasoning
        FROM entries
        WHERE type = 'gotcha'
        ORDER BY timestamp DESC
        LIMIT 30
    """
    )

    gotchas = cursor.fetchall()
    for content, reasoning in gotchas:
        response = f"Gotcha: {content}"
        if reasoning:
            response += f"\n\nDetails: {reasoning}"
        examples.append(
            {
                "instruction": f"What should I watch out for in {project_name}?",
                "context": f"{project_name} - constraint/gotcha",
                "response": response,
            }
        )

    # Get preferences (coding style, patterns)
    cursor.execute(
        """
        SELECT content, category
        FROM entries
        WHERE type = 'preference'
        ORDER BY timestamp DESC
        LIMIT 20
    """
    )

    preferences = cursor.fetchall()
    for content, category in preferences:
        examples.append(
            {
                "instruction": f"What are the {category or 'coding'} preferences for {project_name}?",
                "context": f"{project_name} - team preferences",
                "response": content,
            }
        )

    conn.close()
    print(f"  ✓ Extracted {len(examples)} entries")

    return examples


def format_for_training(examples):
    """Convert to Alpaca format for fine-tuning."""
    training_data = []

    for ex in examples:
        formatted = {"instruction": ex["instruction"], "input": ex.get("context", ""), "output": ex["response"]}
        training_data.append(formatted)

    return training_data


def load_config(config_path):
    """Load configuration from JSON file."""
    with open(config_path) as f:
        config = json.load(f)
    return config


def main():
    parser = argparse.ArgumentParser(description="Generate training data from codebase")
    parser.add_argument("--config", help="Load settings from config.json")
    parser.add_argument("--project", help="Project name")
    parser.add_argument("--src", nargs="+", help="Source directories to analyze")

    # LLM backend options
    llm_group = parser.add_mutually_exclusive_group()
    llm_group.add_argument("--api-key", help="Anthropic API key (fast, ~$1 cost)")
    llm_group.add_argument(
        "--lm-studio",
        nargs="?",
        const="http://localhost:1234/v1",
        help="Use LM Studio (free, slower). Optional URL, default: http://localhost:1234/v1",
    )

    parser.add_argument("--workshop-db", help="Path to workshop.db (optional)")
    parser.add_argument("--patterns", nargs="+", default=["**/*.py"], help="File patterns to match")
    parser.add_argument("--max-files", type=int, help="Limit number of files to analyze")
    parser.add_argument("--output", default="training.jsonl", help="Output file")
    parser.add_argument("--skip-code", action="store_true", help="Skip code analysis, only use workshop db")
    parser.add_argument("--resume", action="store_true", help="Resume from previous run (useful if interrupted)")

    args = parser.parse_args()

    # Load from config file if provided
    if args.config:
        config = load_config(args.config)
        # Command-line args override config file
        args.project = args.project or config.get("project_name")
        args.src = args.src or config.get("source_directories")
        args.workshop_db = args.workshop_db or config.get("workshop_db")
        args.patterns = args.patterns if args.patterns != ["**/*.py"] else config.get("file_patterns", ["**/*.py"])
        args.max_files = args.max_files or config.get("max_files")
        args.output = (
            args.output
            if args.output == "training.jsonl"
            else args.output or config.get("output_file", "training.jsonl")
        )
        args.skip_code = args.skip_code or config.get("skip_code_analysis", False)
        manual_examples = config.get("examples", [])

        # Load LLM backend config if not specified on command line
        if not args.api_key and not args.lm_studio:
            llm_backend = config.get("llm_backend", {})
            backend_type = llm_backend.get("type", "claude")
            if backend_type == "claude":
                args.api_key = llm_backend.get("api_key")
            elif backend_type == "lm-studio":
                args.lm_studio = llm_backend.get("lm_studio_url", "http://localhost:1234/v1")
    else:
        manual_examples = []

    # Validate required args
    if not args.project:
        parser.error("--project is required (or use --config with project_name)")
    if not args.src and not args.skip_code:
        parser.error("--src is required unless using --skip-code (or use --config with source_directories)")

    print("=" * 80)
    print(f"Training Data Generator - {args.project}")
    print("=" * 80)

    examples = []

    # Add manual examples from config
    if manual_examples:
        print(f"\n📝 Adding {len(manual_examples)} manual examples from config")
        examples.extend(manual_examples)

    # Extract from codebase using LLM
    if not args.skip_code:
        if not args.api_key and not args.lm_studio:
            print("\n⚠️  No LLM backend specified. Use --api-key or --lm-studio")
            print("   Skipping code analysis. Use --skip-code to only use workshop entries.\n")
        else:
            # Create LLM client
            if args.api_key:
                print("\n🤖 Using Claude API (fast)")
                client = LLMClient(backend="claude", api_key=args.api_key)
            else:
                print(f"\n🤖 Using LM Studio at {args.lm_studio} (slower, runs overnight)")
                print("   💡 Tip: Progress is saved every 5 files. Use --resume if interrupted.")
                client = LLMClient(backend="lm-studio", base_url=args.lm_studio)

            # Load previous progress if resuming
            if args.resume:
                prev_examples = load_progress(args.output)
                if prev_examples:
                    print(f"   📂 Loaded {len(prev_examples)} examples from previous run")
                    examples.extend(prev_examples)

            examples.extend(
                extract_from_codebase(
                    client,
                    args.src,
                    args.project,
                    args.patterns,
                    args.max_files,
                    output_file=args.output,
                    resume=args.resume,
                )
            )

    # Extract from workshop database
    if args.workshop_db:
        examples.extend(extract_workshop_entries(args.workshop_db, args.project))

    if not examples:
        print("\n❌ No examples generated. Provide --api-key for code analysis or --workshop-db for entries.")
        return

    # Format and save
    training_data = format_for_training(examples)

    output_path = Path(args.output)
    with open(output_path, "w") as f:
        for item in training_data:
            f.write(json.dumps(item) + "\n")

    # Clean up progress files
    progress_file = output_path.with_suffix(".progress.jsonl")
    state_file = output_path.with_suffix(".state.json")
    if progress_file.exists():
        progress_file.unlink()
    if state_file.exists():
        state_file.unlink()

    print(f"\n{'=' * 80}")
    print(f"✓ Generated {len(training_data)} training examples")
    print(f"✓ Saved to: {output_path}")
    print("\nNext steps:")
    print(f"  1. Review {output_path} and add/edit examples as needed")
    print(f"  2. Update finetune.py to use: training_file = '{output_path}'")
    print("  3. Run: python finetune.py")
    print("=" * 80)


if __name__ == "__main__":
    main()
