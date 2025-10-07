#!/usr/bin/env python3
"""
Fine-tune Qwen 2.5 Coder 7B on Workshop knowledge.
Uses LoRA for memory efficiency - works on RTX 4060 8GB.
"""
import torch
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    TrainingArguments,
    Trainer,
    DataCollatorForLanguageModeling,
)
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from datasets import load_dataset


def format_prompt(example):
    """Format training example into prompt template."""
    instruction = example["instruction"]
    input_text = example["input"]
    output = example["output"]

    if input_text:
        prompt = f"""<|im_start|>system
You are a helpful AI assistant with deep knowledge of the Workshop project.<|im_end|>
<|im_start|>user
{instruction}

Context: {input_text}<|im_end|>
<|im_start|>assistant
{output}<|im_end|>"""
    else:
        prompt = f"""<|im_start|>system
You are a helpful AI assistant with deep knowledge of the Workshop project.<|im_end|>
<|im_start|>user
{instruction}<|im_end|>
<|im_start|>assistant
{output}<|im_end|>"""

    return {"text": prompt}


def main():
    print("=" * 80)
    print("Workshop Fine-tuning - Qwen 2.5 Coder 7B with LoRA")
    print("=" * 80)

    # Configuration
    model_name = "Qwen/Qwen2.5-Coder-7B-Instruct"
    output_dir = "./workshop-qwen-lora"
    training_file = "./workshop_training.jsonl"

    print(f"\nModel: {model_name}")
    print(f"Training data: {training_file}")
    print(f"Output: {output_dir}")

    # Load dataset
    print("\n1. Loading training data...")
    dataset = load_dataset("json", data_files=training_file, split="train")
    dataset = dataset.map(format_prompt, remove_columns=dataset.column_names)
    print(f"   ✓ Loaded {len(dataset)} examples")

    # Load tokenizer
    print("\n2. Loading tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"

    # Tokenize
    def tokenize(example):
        return tokenizer(example["text"], truncation=True, max_length=2048, padding="max_length")

    tokenized_dataset = dataset.map(tokenize, remove_columns=["text"])
    print("   ✓ Tokenized dataset")

    # Load model in 4-bit (saves memory)
    print("\n3. Loading base model (4-bit quantization)...")
    model = AutoModelForCausalLM.from_pretrained(
        model_name, load_in_4bit=True, torch_dtype=torch.float16, device_map="auto", trust_remote_code=True
    )
    model = prepare_model_for_kbit_training(model)
    print("   ✓ Model loaded")

    # LoRA configuration
    print("\n4. Configuring LoRA...")
    lora_config = LoraConfig(
        r=16,  # LoRA rank
        lora_alpha=32,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
    )
    model = get_peft_model(model, lora_config)
    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total_params = sum(p.numel() for p in model.parameters())
    print(f"   ✓ Trainable params: {trainable_params:,} ({100 * trainable_params / total_params:.2f}%)")

    # Training arguments
    print("\n5. Setting up training...")
    training_args = TrainingArguments(
        output_dir=output_dir,
        num_train_epochs=3,
        per_device_train_batch_size=1,
        gradient_accumulation_steps=4,
        learning_rate=2e-4,
        fp16=True,
        logging_steps=10,
        save_strategy="epoch",
        optim="paged_adamw_8bit",
        warmup_steps=50,
        max_grad_norm=0.3,
    )

    # Data collator
    data_collator = DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=False)

    # Trainer
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized_dataset,
        data_collator=data_collator,
    )

    # Train!
    print("\n6. Training...")
    print("   This will take 2-6 hours on RTX 4060")
    print("   GPU temperature: Keep under 85°C")
    print("   Starting training...\n")

    trainer.train()

    # Save
    print("\n7. Saving fine-tuned model...")
    model.save_pretrained(output_dir)
    tokenizer.save_pretrained(output_dir)

    print("\n" + "=" * 80)
    print("✓ Fine-tuning complete!")
    print(f"✓ Model saved to: {output_dir}")
    print("\nNext: Run inference.py to test the model")
    print("=" * 80)


if __name__ == "__main__":
    main()
