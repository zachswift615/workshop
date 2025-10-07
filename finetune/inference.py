#!/usr/bin/env python3
"""
Run the Workshop-trained model locally.
Ask it questions about Workshop without needing RAG/context retrieval!
"""
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel


def load_model(base_model_name="Qwen/Qwen2.5-Coder-7B-Instruct", lora_path="./workshop-qwen-lora"):
    """Load the fine-tuned model."""
    print("Loading model...")

    tokenizer = AutoTokenizer.from_pretrained(base_model_name)

    # Load base model
    base_model = AutoModelForCausalLM.from_pretrained(
        base_model_name, load_in_4bit=True, torch_dtype=torch.float16, device_map="auto", trust_remote_code=True
    )

    # Load LoRA weights
    model = PeftModel.from_pretrained(base_model, lora_path)

    print("✓ Model loaded\n")
    return model, tokenizer


def ask(model, tokenizer, question, context=""):
    """Ask the model a question about Workshop."""
    if context:
        prompt = f"""<|im_start|>system
You are a helpful AI assistant with deep knowledge of the Workshop project.<|im_end|>
<|im_start|>user
{question}

Context: {context}<|im_end|>
<|im_start|>assistant
"""
    else:
        prompt = f"""<|im_start|>system
You are a helpful AI assistant with deep knowledge of the Workshop project.<|im_end|>
<|im_start|>user
{question}<|im_end|>
<|im_start|>assistant
"""

    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)

    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=512,
            temperature=0.7,
            top_p=0.9,
            do_sample=True,
            pad_token_id=tokenizer.eos_token_id,
        )

    response = tokenizer.decode(outputs[0], skip_special_tokens=True)
    # Extract just the assistant's response
    response = response.split("<|im_start|>assistant")[-1].strip()

    return response


def main():
    print("=" * 80)
    print("Workshop-trained Model - Interactive Mode")
    print("=" * 80)

    model, tokenizer = load_model()

    print("Ask questions about Workshop! (type 'quit' to exit)\n")

    # Example questions
    examples = [
        "How does Workshop store entries?",
        "What CLI commands are available?",
        "Explain Workshop's architecture",
        "Why did we use SQLAlchemy instead of raw SQL?",
    ]

    print("Example questions:")
    for i, ex in enumerate(examples, 1):
        print(f"  {i}. {ex}")
    print()

    while True:
        question = input("Question: ")
        if question.lower() in ["quit", "exit", "q"]:
            break

        if not question.strip():
            continue

        print("\nThinking...\n")
        response = ask(model, tokenizer, question)
        print(f"Answer: {response}\n")
        print("-" * 80 + "\n")


if __name__ == "__main__":
    main()
