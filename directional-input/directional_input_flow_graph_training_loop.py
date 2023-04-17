# -*- coding: utf-8 -*-
"""Directional Input Flow Graph Training Loop.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1x-sxvpZn95XkfCa1ZhNJlT6V8M0iwjs3
"""

# Imports for Data Processing
import pandas as pd
import numpy as np
import torch
import argparse

from transformers import AutoModelForSequenceClassification, AutoTokenizer, DataCollatorWithPadding, get_scheduler
from datasets import load_from_disk
from accelerate import Accelerator

from torch.utils.data import DataLoader

from tqdm.auto import tqdm
from matplotlib import pyplot as plt

from sklearn.metrics import precision_score, recall_score, f1_score, classification_report

from collections import defaultdict

PROJECT_DIR = '/home/sejipark/NLP-FYP-HPC/'
MODEL_CHECKPOINT = "bert-base-cased"

parser = argparse.ArgumentParser()
parser.add_argument('--t', type=str, help='Recipe Corpus Target: can either be r-100, r-200, or r-300')
parser.add_argument('--us', type=float, help='Undersample Factor: value between 0.0 and 1.0')
parser.add_argument('--epochs', type=int, help='Number of Epochs')
parser.add_argument('--weighted', action='store_true', help='Toggling Weighted Cross Entropy Loss')

args = parser.parse_args()

TARGET_CORPUS = args.t
UNDERSAMPLE_FACTOR = args.us
OUTPUT_DIR = PROJECT_DIR + 'outputs/directional-input-flow/' + TARGET_CORPUS + '-' + str(UNDERSAMPLE_FACTOR) + '/' + MODEL_CHECKPOINT + '/'
WEIGHTED_CROSS_ENTROPY = args.weighted

device = torch.device('cpu')

if torch.cuda.is_available():
  device = torch.device('cuda')

corpus_datasets = load_from_disk(PROJECT_DIR + 'datasets/' + TARGET_CORPUS + '-' + str(UNDERSAMPLE_FACTOR) + '-directional-input-flow')

tokenizer = AutoTokenizer.from_pretrained(MODEL_CHECKPOINT)

def tokenize_function(data):
  return tokenizer(data["Word Pairs"], data["Sentence Pairs"], add_special_tokens=True, max_length=128, padding='max_length')

tokenized_datasets = corpus_datasets.map(tokenize_function, batched=True)
data_collator = DataCollatorWithPadding(tokenizer=tokenizer)

tokenized_datasets = tokenized_datasets.remove_columns(["Word Pairs", "Sentence Pairs"])
tokenized_datasets = tokenized_datasets.rename_column("Label", "labels")

train_dataloader = DataLoader(
    tokenized_datasets["train"], batch_size=32, collate_fn=data_collator
)

eval_dataloader = DataLoader(
    tokenized_datasets["valid"], batch_size=32, collate_fn=data_collator
)

label_names = tokenized_datasets["train"].features["labels"].names

id2label = {i: label for i, label in enumerate(label_names)}
label2id = {v: k for k, v in id2label.items()}

def evaluate(dataloader_val):
    flow_model.eval()
    
    loss_val_total = 0
    pred_vals, true_vals = [], []
    
    for batch in dataloader_val:
        with torch.no_grad():        
            outputs = flow_model(**batch)

        loss = outputs.get("loss")
        loss_val_total += loss.item()

        logits = outputs.get("logits")
        predictions = logits.argmax(dim=-1).detach().cpu().numpy()
        
        label_ids = batch.get('labels').detach().cpu().numpy()

        pred_vals.append(predictions)
        true_vals.append(label_ids)
    
    pred_vals = np.concatenate(pred_vals)
    true_vals = np.concatenate(true_vals)

    perf_metrics = {
        "overall_precision": precision_score(true_vals, pred_vals, average="weighted"),
        "overall_recall": recall_score(true_vals, pred_vals, average="weighted"),
        "overall_f1": f1_score(true_vals, pred_vals, average="weighted"),
    }

    loss_val_avg = loss_val_total/len(dataloader_val) 

    return perf_metrics, loss_val_avg, pred_vals, true_vals

# Calculate Weights for Cross Entropy Loss

weights = []

if WEIGHTED_CROSS_ENTROPY:
  num_labels = len(label_names)
  frequencies = [0] * num_labels

  for batch in train_dataloader:
    for label in batch['labels']:
        frequencies[label] += 1

  weights = [1 / frequency for frequency in frequencies]
  weights = torch.tensor(weights).to(device)

accelerator = Accelerator()

flow_model = AutoModelForSequenceClassification.from_pretrained(
    MODEL_CHECKPOINT, 
    id2label=id2label,
    label2id=label2id,
    num_labels=len(label_names)
)

param_optimizer = list(flow_model.named_parameters())
no_decay = ['bias', 'gamma', 'beta']
optimizer_grouped_parameters = [
    {'params': [p for n, p in param_optimizer if not any(nd in n for nd in no_decay)],
    'weight_decay_rate': 0.01},
    {'params': [p for n, p in param_optimizer if any(nd in n for nd in no_decay)],
    'weight_decay_rate': 0.0}]

optimizer = torch.optim.AdamW(optimizer_grouped_parameters, lr=3e-5)

train_dl, eval_dl, flow_model, optimizer = accelerator.prepare(
    train_dataloader, eval_dataloader, flow_model, optimizer
)

loss_fct = torch.nn.CrossEntropyLoss()

if WEIGHTED_CROSS_ENTROPY:
  loss_fct = torch.nn.CrossEntropyLoss(weight=weights)

epochs = args.epochs
num_training_steps = epochs * len(train_dl)
lr_scheduler = get_scheduler(
    "linear",
    optimizer=optimizer,
    num_warmup_steps=0,
    num_training_steps=num_training_steps,
)

progress_bar = tqdm(range(num_training_steps))

overall_metrics = defaultdict(list)
train_loss_vals, eval_loss_vals = [], []

for epoch in range(epochs):
    # Training
    train_loss_sum = 0
    flow_model.train()
    for batch in train_dl:
        labels = batch.get("labels")
        outputs = flow_model(**batch)
        logits = outputs.get("logits")

        loss = loss_fct(logits.view(-1, flow_model.config.num_labels), labels.view(-1))
        train_loss_sum += loss.item()

        accelerator.backward(loss)

        optimizer.step()
        lr_scheduler.step()
        optimizer.zero_grad()
        progress_bar.update(1)
    
    train_loss = train_loss_sum / len(train_dl)
    train_loss_vals.append(train_loss)

    # Evaluation
    perf_metrics, val_loss, _, _ = evaluate(eval_dl)

    for key in ["precision", "recall", "f1"]:
        overall_metrics[key].append(perf_metrics[f"overall_{key}"] * 100)

    eval_loss_vals.append(val_loss)

flow_model.save_pretrained(OUTPUT_DIR + 'model/' + TARGET_CORPUS + '-' + MODEL_CHECKPOINT + '-model')

plt.plot(range(1, epochs+1), train_loss_vals, label='Training Loss')
plt.plot(range(1, epochs+1), eval_loss_vals, label='Validation Loss')

plt.title('Loss for ' + MODEL_CHECKPOINT + ' Model with ' + str(int((1.0 - UNDERSAMPLE_FACTOR) * 100)) + '% Undersampled ' + TARGET_CORPUS + ' Dataset')
plt.xlabel('Epochs')
plt.xticks(range(1, epochs+1), [int(i) for i in range(1, epochs+1)])

plt.ylabel('Loss')
plt.ylim(0, None)

plt.legend()

plt.savefig(OUTPUT_DIR + "train_valid_losses.png")

plt.clf()
for key in ["precision", "recall", "f1"]:
  plt.plot(range(1, epochs+1), overall_metrics[key], label = key + ' score')

plt.title('Weighted Metrics for ' + MODEL_CHECKPOINT + ' Model with ' + str(int((1.0 - UNDERSAMPLE_FACTOR) * 100)) + '% Undersampled ' + TARGET_CORPUS + ' Dataset')
plt.xlabel('Epochs')
plt.xticks(range(1, epochs+1), [int(i) for i in range(1, epochs+1)])

plt.ylabel('Score')
plt.ylim(None, 100)

plt.legend()
plt.savefig(OUTPUT_DIR + "metrics.png")

_, _, pred_vals, true_vals = evaluate(eval_dl)

labeled_preds = [label_names[pred_val] for pred_val in pred_vals]
labeled_trues = [label_names[true_val] for true_val in true_vals]

report = classification_report(labeled_trues, labeled_preds, output_dict=True)

df = pd.DataFrame(report).transpose()
df.to_csv(OUTPUT_DIR + 'classification_report.csv')