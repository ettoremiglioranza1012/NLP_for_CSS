import os
os.environ["TRANSFORMERS_NO_TF"] = "1"  # Disable TensorFlow/Keras (fixes Keras 3 issue)

from transformers import RobertaTokenizer, RobertaForSequenceClassification
from transformers import TrainingArguments, Trainer
import pandas as pd
from datasets import Dataset
import torch

# Detect Apple Silicon (M1/M2/M3) GPU or fallback to CPU
device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")

# Tokenization function for batched inputs
def tokenize(batch):
    return tokenizer(batch['text'], padding="max_length", truncation=True, max_length=128)

if __name__ == "__main__":
    # Load pretrained tokenizer and classification model
    tokenizer = RobertaTokenizer.from_pretrained("roberta-base")
    model = RobertaForSequenceClassification.from_pretrained("roberta-base", num_labels=2)
    model.to(device)  # Move model to Apple GPU or CPU

    ## Load and prepare dataset ##
    df = pd.read_csv("/Users/tommasocestari/Downloads/GoldStandard2024.csv")

    # Keep only relevant columns and rename for Trainer compatibility
    df_clean = df[["Text", "Biased"]].rename(columns={"Text": "text", "Biased": "label"})

    # Create Hugging Face Dataset and tokenize it
    dataset = Dataset.from_pandas(df_clean)
    tokenized_dataset = dataset.map(tokenize, batched=True)

    # Split once and reuse both sets
    split = tokenized_dataset.train_test_split(test_size=0.2, seed=42)
    train_dataset = split['train']
    eval_dataset = split['test']

    ## Training setup ##
    training_args = TrainingArguments(
        output_dir="./roberta-antisemitism",       # Where to save model
        eval_strategy="epoch",               # Eval every epoch
        learning_rate=2e-5,
        per_device_train_batch_size=8,
        per_device_eval_batch_size=8,
        num_train_epochs=3,
        weight_decay=0.01,
        logging_dir="./logs",                      # Optional: log dir
        logging_steps=10,
        save_strategy="epoch",                     # Save model every epoch
        push_to_hub=False                          # Disable HF Hub upload
    )

    # Initialize Trainer
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        tokenizer=tokenizer,
    )

    # Start training
    trainer.train()

    # Save model + tokenizer (optional for inference later)
    model.save_pretrained("./roberta-antisemitism")
    tokenizer.save_pretrained("./roberta-antisemitism")
