from transformers import RobertaTokenizer, RobertaForSequenceClassification
import torch
import sys
import os
from evaluation_msg import texts, truth

# Use absolute path to avoid validation issues
model_path = os.path.abspath("./roberta-antisemitism")

# Load fine-tuned model and tokenizer
model = RobertaForSequenceClassification.from_pretrained(model_path, local_files_only=True)
tokenizer = RobertaTokenizer.from_pretrained(model_path, local_files_only=True)
model.eval()

# Use MPS if available
device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
model.to(device)

model_predictions = []
for text in texts:
    inputs = tokenizer(text, return_tensors="pt", padding="max_length", truncation=True, max_length=128)
    inputs = {k: v.to(device) for k, v in inputs.items()}  # move to device
    
    with torch.no_grad():
        logits = model(**inputs).logits
        prediction = torch.argmax(logits, dim=1).item()
        label = 1 if prediction == 1 else 0
        print(f"{text} -> {label}")
        model_predictions.append(label)

