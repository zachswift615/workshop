# Quick Start: Fine-tune on Workshop with LM Studio

You already have LM Studio with Qwen! Here's how to use it **completely free** to generate training data overnight:

## 1. Start LM Studio

1. Open LM Studio
2. Load your Qwen 2.5 Coder model (or any chat model)
3. Go to the "Local Server" tab
4. Click "Start Server"
5. Make sure it says "Server running on http://localhost:1234"

## 2. Generate Training Data (Run Overnight)

```bash
cd finetune

# Option 1: Just Workshop entries (fastest, no LLM needed)
python generate_training_data.py \
  --project "Workshop" \
  --workshop-db ../.workshop/workshop.db \
  --skip-code \
  --output workshop_training.jsonl

# Option 2: Analyze code + Workshop entries (free, runs overnight)
python generate_training_data.py \
  --project "Workshop" \
  --src ../workshop/src \
  --workshop-db ../.workshop/workshop.db \
  --lm-studio \
  --output workshop_training.jsonl
```

**If it gets interrupted** (crash, power loss, etc.), just resume:
```bash
python generate_training_data.py \
  --project "Workshop" \
  --src ../workshop/src \
  --workshop-db ../.workshop/workshop.db \
  --lm-studio \
  --resume \
  --output workshop_training.jsonl
```

Progress saves every 5 files automatically!

## 3. Fine-tune (2-6 hours on your RTX 4060)

```bash
# Make sure finetune.py line 51 points to your training file
python finetune.py
```

This will:
- Use 4-bit quantization (fits in 8GB VRAM)
- Train for 3 epochs
- Save LoRA weights to `./workshop-qwen-lora/`

## 4. Use Your Model

```bash
python inference.py
```

Now ask it questions about Workshop:
- "How does Workshop store entries?"
- "What CLI commands are available?"
- "Why did we use SQLAlchemy instead of raw SQL?"

The model will answer from learned knowledge, not retrieval!

## Speed Comparison

**Option 1** (Workshop entries only):
- No LLM needed
- Completes in seconds
- Good starting point

**Option 2** (LM Studio analyzing code):
- Takes 4-12 hours for ~100 files
- Completely free
- Run overnight
- Better training data (includes code explanations)

**Claude API** (not using this, but for reference):
- Takes 10-30 minutes
- Costs ~$1
- Best quality training data

## Tips

1. **Start with Option 1** to test the workflow end-to-end
2. **Then try Option 2** overnight to get better training data
3. **Monitor progress**: The script shows files processed and time remaining
4. **Check the .jsonl file** before training to see what it learned
5. **Iterate**: Re-run periodically as you add more Workshop entries
