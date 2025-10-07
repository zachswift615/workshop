# Fine-tune an LLM on Your Codebase

Bake project knowledge into a local LLM instead of using RAG/retrieval.

## Quick Start - Any Project

### 1. Generate Training Data

**Option A: Use a config file (easiest)**
```bash
# Copy the example config
cp config.example.json config.json

# Edit config.json with your project settings
# Then run:
python generate_training_data.py --config config.json --api-key $ANTHROPIC_API_KEY
```

**Option B: Claude API (fast, ~$1 cost, 10-30 minutes)**
```bash
# Analyze your codebase and generate Q&A pairs
python generate_training_data.py \
  --project "MyProject" \
  --src ../src \
  --api-key $ANTHROPIC_API_KEY \
  --output my_training.jsonl

# Include Workshop entries too:
python generate_training_data.py \
  --project "MyProject" \
  --src ../src ../lib \
  --workshop-db ../.workshop/workshop.db \
  --api-key $ANTHROPIC_API_KEY \
  --output my_training.jsonl
```

**Option C: LM Studio (free, slower, run overnight)**
```bash
# 1. Start LM Studio and load Qwen 2.5 Coder or similar model
# 2. Enable API server in LM Studio (default: http://localhost:1234)
# 3. Run generation:

python generate_training_data.py \
  --project "MyProject" \
  --src ../src \
  --lm-studio \
  --output my_training.jsonl

# Progress saves every 5 files. If interrupted, resume with:
python generate_training_data.py \
  --project "MyProject" \
  --src ../src \
  --lm-studio \
  --resume \
  --output my_training.jsonl
```

**Option D: Only Workshop entries (no LLM needed)**
```bash
# Just use your workshop decisions/gotchas/preferences
python generate_training_data.py \
  --project "MyProject" \
  --workshop-db ../.workshop/workshop.db \
  --skip-code \
  --output my_training.jsonl
```

### 2. Fine-tune the Model

```bash
# Update finetune.py line 51 to point to your training file:
# training_file = "./my_training.jsonl"

# Then train (2-6 hours on RTX 4060)
python finetune.py
```

### 3. Use Your Fine-tuned Model

```bash
# Chat with a model that "knows" your codebase
python inference.py
```

## Advanced Options

### Analyze Multiple Directories
```bash
python generate_training_data.py \
  --project "MyApp" \
  --src ../frontend/src ../backend/src ../shared \
  --patterns "**/*.ts" "**/*.tsx" "**/*.py" \
  --output myapp_training.jsonl
```

### Limit Number of Files (for faster testing)
```bash
python generate_training_data.py \
  --project "Test" \
  --src ../src \
  --max-files 10 \
  --output test_training.jsonl
```

## What Gets Learned?

The model learns:
- **Code structure**: What functions/classes do, how to use them
- **Architecture**: Why things are designed the way they are
- **Decisions**: From your workshop entries (if included)
- **Gotchas**: Common pitfalls and constraints
- **Patterns**: Coding style and best practices

## Requirements

```bash
# For training data generation with Claude API:
pip install anthropic

# For training data generation with LM Studio:
pip install openai

# For fine-tuning:
pip install transformers peft datasets bitsandbytes torch accelerate
```

**Hardware**: Works on RTX 4060 8GB (or any 8GB+ GPU)

## Example: Workshop Project

For this Workshop project specifically:
```bash
# Generate training data
python generate_training_data.py \
  --project "Workshop" \
  --src ../workshop/src \
  --workshop-db ../.workshop/workshop.db \
  --api-key $ANTHROPIC_API_KEY \
  --output workshop_training.jsonl

# Fine-tune
python finetune.py

# Test
python inference.py
```

## Cost

**With Claude API:**
- Training data generation: ~$0.50-2 (fast, 10-30 min)
- Fine-tuning: Free (runs on your GPU, 2-6 hours)
- Inference: Free (runs locally)
- **Total: < $5**

**With LM Studio:**
- Training data generation: **FREE** (slower, run overnight)
- Fine-tuning: Free (runs on your GPU, 2-6 hours)
- Inference: Free (runs locally)
- **Total: $0**

## Tips

1. **Start small**: Use `--max-files 10` to test the workflow first
2. **LM Studio overnight**: Start it before bed with `--lm-studio`, check progress in the morning. Uses `--resume` if interrupted.
3. **Review the data**: Check the .jsonl file before training
4. **Add manual examples**: Edit the .jsonl to add specific knowledge you want
5. **Keep using Workshop**: More entries = better training data for next iteration
6. **Iterate**: Re-train periodically as your project evolves
