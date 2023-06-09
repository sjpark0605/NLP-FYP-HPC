# -*- coding: utf-8 -*-
"""NER Data Processing.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1-fSfpUJynIsz-Qhotb7WnecraWWdtbAT
"""

# Commented out IPython magic to ensure Python compatibility.
# %%capture
# !pip install datasets

import argparse
import csv

# Imports for Data Processing
import glob

import pandas as pd
from datasets import ClassLabel, Dataset, DatasetDict, Sequence

PROJECT_DIR = "/cluster/project2/COMP0029_17022125/NLP-FYP-HPC/"
SEED = 2023

parser = argparse.ArgumentParser()
parser.add_argument(
    "--t", type=str, help="Recipe Corpus Target: can either be r-100, r-200, or r-300"
)

args = parser.parse_args()

TARGET_CORPUS = args.t
print("Preprocessing " + TARGET_CORPUS + " Corpus")

max_word_count = 0

recipe_files = []

if TARGET_CORPUS != "r-300":
    recipe_files += glob.glob(PROJECT_DIR + TARGET_CORPUS + "/*.list")
else:
    recipe_files += glob.glob(PROJECT_DIR + "r-100/*.list")
    recipe_files += glob.glob(PROJECT_DIR + "r-200/*.list")

recipe_ner_data_csv = open(
    PROJECT_DIR + TARGET_CORPUS + "-recipe-ner-data.csv", "w", encoding="utf-8"
)
writer = csv.writer(recipe_ner_data_csv)

header = ["Sentence Number", "Word", "POS", "Label"]
writer.writerow(header)

sentence_no = 1

for file in recipe_files:
    word_count = 0
    recipe_data = open(file, "r", encoding="utf-8")
    lines = recipe_data.readlines()

    for line in lines:
        items = line.split(" ")
        word = items[3]
        pos = items[4]
        label = items[5].replace("\n", "")
        word_count += 1

        row = ["Sentence_" + str(sentence_no), word, pos, label]
        writer.writerow(row)

        if pos == ".":
            sentence_no += 1

    max_word_count = max(word_count, max_word_count)

    recipe_data.close()

recipe_ner_data_csv.close()
max_word_count

df = pd.read_csv(PROJECT_DIR + TARGET_CORPUS + "-recipe-ner-data.csv")
pos_list = df["POS"].unique()
label_list = sorted(df["Label"].unique())

label_list.remove("O")
label_list.append("O")

grouped = (
    df.groupby("Sentence Number")
    .agg({"Word": list, "POS": list, "Label": list})
    .reset_index()
)
grouped.drop("Sentence Number", axis=1, inplace=True)
grouped.rename(
    columns={"Word": "tokens", "POS": "pos", "Label": "ner_tags"}, inplace=True
)

dataset = Dataset.from_pandas(grouped)
dataset = dataset.cast_column("pos", Sequence(ClassLabel(names=list(pos_list))))
dataset = dataset.cast_column("ner_tags", Sequence(ClassLabel(names=list(label_list))))

dataset = dataset.shuffle(seed=SEED)
split_dataset = dataset.train_test_split(test_size=0.2)

corpus_datasets = DatasetDict(
    {"train": split_dataset["train"], "valid": split_dataset["test"]}
)

corpus_datasets.save_to_disk(PROJECT_DIR + "datasets/" + TARGET_CORPUS + "-ner")
