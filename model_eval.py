from transformers import RobertaTokenizer, RobertaForSequenceClassification
import torch
import sys
from evaluation_msg import texts, truth

# Load fine-tuned model and tokenizer
model = RobertaForSequenceClassification.from_pretrained("./roberta-antisemitism")
tokenizer = RobertaTokenizer.from_pretrained("./roberta-antisemitism")
model.eval()

# Use MPS if available
device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
model.to(device)


model_predictions = []
for text in texts:
    inputs = tokenizer(text, return_tensors="pt", padding="max_length", truncation=True, max_length=128)
    inputs = {k: v.to(device) for k, v in inputs.items()}  # move to GPU
    with torch.no_grad():
        logits = model(**inputs).logits
        prediction = torch.argmax(logits, dim=1).item()
    
    label = 1 if prediction == 1 else 0
    # print(f"{label}")
    model_predictions.append(label)

count = 0
#for i in range(len(model_predictions)):
#     if model_predictions[i] == truth[i]:
#         count += 1
# print(count)

    #### uncomment to see misclassified messages ####
    # if model_predictions[i] != truth[i]:
    #     print(texts[i])


### FP ###
FP = 0
FN = 0

for i in range(len(texts)):
    if model_predictions[i] == 1 and truth[i] == 0:
        FP += 1
        print(f"False positive : {texts[i]}")
    elif model_predictions[i] == 0 and truth[i] == 1:
        FN += 1
        print(f"False negative : {texts[i]}")