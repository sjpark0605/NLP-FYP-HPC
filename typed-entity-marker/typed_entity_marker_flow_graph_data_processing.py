# -*- coding: utf-8 -*-
"""Entity Marker Flow Recipe Data Processing.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1KshNjMH6kXD6erJqjUdCD-nLwEDoG_MD
"""

# Imports for Data Processing
import glob
import numpy as np
import pandas as pd
import pickle
import argparse

from datasets import Dataset, ClassLabel, DatasetDict

PROJECT_DIR = '/home/sejipark/NLP-FYP-HPC/'
SEED = 2023

parser = argparse.ArgumentParser()
parser.add_argument('--t', type=str, help='Recipe Corpus Target: can either be r-100, r-200, or r-300')
parser.add_argument('--us', type=float, help='Undersample Factor: value between 0.0 and 1.0')

args = parser.parse_args()

TARGET_CORPUS = args.t
UNDERSAMPLE_FACTOR = args.us

GLOBAL_INCLUDED_COUNT, GLOBAL_REJECTED_COUNT, GLOBAL_EDGE_COUNT = 0, 0, 0

NER_FILES, FLOW_FILES = [], []

if TARGET_CORPUS == 'r-100' or TARGET_CORPUS == 'r-200':
  NER_FILES += glob.glob(PROJECT_DIR + TARGET_CORPUS + '/*.list')
  FLOW_FILES += glob.glob(PROJECT_DIR + TARGET_CORPUS + '/*.flow')
elif TARGET_CORPUS == 'r-300':
  for corpus in ['r-100', 'r-200']:
    NER_FILES += glob.glob(PROJECT_DIR + corpus + '/*.list')
    FLOW_FILES += glob.glob(PROJECT_DIR + corpus + '/*.flow')
else:
  raise Exception("Could not recognize target corpus")

NER_FILES.sort()
FLOW_FILES.sort()

def encode_key(decoded_key):
  if len(decoded_key) != 3:
    raise Exception("Malformed Key During Encoding: Length != 3")
  
  return str(decoded_key[0]) + ';' + str(decoded_key[1]) + ';' + str(decoded_key[2])

def decode_key(encoded_key):
  encoded_key = encoded_key.split(';')

  if len(encoded_key) != 3:
    raise Exception("Malformed Key During Decoding: Length != 3")
  return (int(encoded_key[0]), int(encoded_key[1]), int(encoded_key[2]))

def construct_recipe_dict(ner_lines, remove_iob = False):
  word_dict = {}
  ner_dict = {}

  for line in ner_lines:
    items = line.strip().split(" ")

    key, word, ner_tag = encode_key(items[:3]), items[3], items[5]

    if remove_iob:
      ner_tag = ner_tag.replace("-B", "").replace("-I", "")

    word_dict[key] = word
    ner_dict[key] = ner_tag
  
  return word_dict, ner_dict

def construct_label_dict(flow_lines):
  global GLOBAL_EDGE_COUNT
  recipe_dict = {}
  
  for line in flow_lines:
    GLOBAL_EDGE_COUNT += 1
    items = line.strip().split(" ")

    source_node = (int(items[0]), int(items[1]), int(items[2]))
    dest_node = (int(items[4]), int(items[5]), int(items[6]))

    label = items[3]
    if label == "v":
      label = "v-tm"
    elif label == "s":
      label = "d"

    if source_node < dest_node:
      label += ":LR"
      recipe_dict[(source_node, dest_node)] = label
    else:
      label += ":RL"
      recipe_dict[(dest_node, source_node)] = label
  
  return recipe_dict

RELATION_SET = set()

for ner_file, flow_file in zip(NER_FILES, FLOW_FILES):
  ner_data, flow_data = open(ner_file, "r", encoding="utf-8"), open(flow_file, "r", encoding="utf-8")
  ner_lines, flow_lines = ner_data.readlines(), flow_data.readlines()

  _, ner_dict = construct_recipe_dict(ner_lines)

  for line in flow_lines:
    items = line.strip().split(" ")
    source_key, dest_key = encode_key(items[:3]), encode_key(items[4:])

    relation = ner_dict[source_key] + "->" + ner_dict[dest_key]

    RELATION_SET.add(relation)

  ner_data.close()
  flow_data.close()

with open(PROJECT_DIR + TARGET_CORPUS + "-relation_set.pickle", "wb") as relation_set_file:
    pickle.dump(RELATION_SET, relation_set_file)

def generate_pairs(ner_lines, ner_dict):
  global GLOBAL_INCLUDED_COUNT
  global GLOBAL_REJECTED_COUNT

  positions, pairs = [], []

  for line in ner_lines:
    items = line.split(" ")
    label = items[5].replace("\n", "")

    if "-I" not in label and label != "O":
      position = (int(items[0]), int(items[1]), int(items[2]))
      positions.append(position)

  for i in range(len(positions)):
    for j in range(i+1, len(positions)):
      source_key, dest_key = encode_key(positions[i]), encode_key(positions[j])
      source_ner, dest_ner = ner_dict[source_key], ner_dict[dest_key]

      flow1 = source_ner + "->" + dest_ner
      flow2 = dest_ner + "->" + source_ner

      if flow1 in RELATION_SET or flow2 in RELATION_SET:
        pairs.append((positions[i], positions[j]))
        GLOBAL_INCLUDED_COUNT += 1
      else:
        GLOBAL_REJECTED_COUNT += 1

  return pairs

def construct_sentence(ner_lines, ner_dict, position, target_word_positions, typed=False):
  first_word = True
  sentence = ""

  marking = -1
  marking_ner_tag = None

  for line in ner_lines:
    items = line.strip().split(" ")
    items[0], items[1], items[2] = int(items[0]), int(items[1]), int(items[2])

    if (position[0], position[1]) == (items[0], items[1]):

      if marking != -1:
        word_key = encode_key((items[0], items[1], items[2]))
        
        if marking_ner_tag.replace('-B', '-I') != ner_dict[word_key]:
          sentence += (' </e' + str(marking) + '>')
          marking, marking_ner_tag = -1, None

      if not first_word:
        sentence += " "

      first_word = False
      word_added = False

      for index, target_word_position in enumerate(target_word_positions):
        if target_word_position == (items[0], items[1], items[2]):
          word_key = encode_key(target_word_position)
          marking, marking_ner_tag = index + 1, ner_dict[word_key]

          sentence += ('<e' + str(marking) + ' type=' + marking_ner_tag.replace('-B', '').replace('-I','') + '> ' + items[3])
          word_added = True

      if not word_added:
        sentence += items[3]

  if marking != -1:
    sentence += (' </e' + str(marking) + '>')

  return sentence

def check_sentence_sanity(sentence):
  contains_marking = False

  entities = ['Ac', 'Ac2', 'Af', 'At', 'D', 'F', 'Q', 'Sf', 'St', 'T']
  marker_pairs = []

  for entity in entities:
    marker_pairs.append(('<e1 type=' + entity + '>', '</e1>'))
    marker_pairs.append(('<e2 type=' + entity + '>', '</e2>'))

  for opening_tag, closing_tag in marker_pairs:
    if opening_tag in sentence:
      contains_marking = True 

      if closing_tag not in sentence:
        raise Exception(closing_tag + " is missing!")

  if not contains_marking:
    raise Exception("no tags found!")

def construct_data():
  first_sentences, second_sentences, labels = [], [], []

  for ner_file, flow_file in zip(NER_FILES, FLOW_FILES):
    ner_data, flow_data = open(ner_file, "r", encoding="utf-8"), open(flow_file, "r", encoding="utf-8")

    ner_lines, flow_lines = ner_data.readlines(), flow_data.readlines()
    
    word_dict, ner_dict = construct_recipe_dict(ner_lines)
    label_dict = construct_label_dict(flow_lines)

    if word_dict.keys() != ner_dict.keys():
      raise Exception("Malformed Word and NER Dictionary")

    word_pairs = generate_pairs(ner_lines, ner_dict)

    for word_pair in word_pairs:
      sentence1 = construct_sentence(ner_lines, ner_dict, position=word_pair[0], target_word_positions=word_pair)
      sentence2 = construct_sentence(ner_lines, ner_dict, position=word_pair[1], target_word_positions=word_pair)

      check_sentence_sanity(sentence1)
      check_sentence_sanity(sentence2)

      if sentence1 == sentence2:
        first_sentences.append(sentence1)
        second_sentences.append(None)
      else:
        first_sentences.append(sentence1)
        second_sentences.append(sentence2)

      if (word_pair[0], word_pair[1]) in label_dict:
        labels.append(label_dict[(word_pair[0], word_pair[1])])
      else:
        labels.append('non-edge')

    ner_data.close()
    flow_data.close()
  
  return first_sentences, second_sentences, labels

first_sentences, second_sentences, labels = construct_data()

np_first_sentences, np_second_sentences, np_labels = np.array(first_sentences), np.array(second_sentences), np.array(labels)

data_matrix = np.column_stack((np_first_sentences, np_second_sentences, np_labels))

df = pd.DataFrame(data_matrix, columns=['First Sentence', 'Second Sentence', 'Label'])

if TARGET_CORPUS != 'r-300':
  # Duplicate a 't-eq:RL' occurrence since there is only one occurrence in the r-100 and r-200 datasets
  row = df.loc[df['Label'] == 't-eq:RL']
  df = pd.concat([df, row], ignore_index=True)

def undersample(df, undersample_factor):
  match_indices = df.index[df['Label'] == 'non-edge']
  np.random.seed(SEED)
  delete_indices = np.random.choice(match_indices, size=int(len(match_indices) * undersample_factor), replace=False)
  df = df.drop(delete_indices)
  df = df.reset_index(drop=True)
  
  return df

df = undersample(df, UNDERSAMPLE_FACTOR)
df['Label'].value_counts()['non-edge'] / df['Label'].value_counts().sum()

edge_label_list = df['Label'].unique()

dataset = Dataset.from_pandas(df)
ClassLabels = ClassLabel(num_classes=len(edge_label_list), names=list(edge_label_list))
dataset = dataset.class_encode_column("Label", ClassLabels)

dataset = dataset.shuffle(seed=SEED)
split_dataset = dataset.train_test_split(test_size=0.2, stratify_by_column="Label")

corpus_datasets = DatasetDict({
    "train": split_dataset["train"],
    "valid": split_dataset["test"],
})

corpus_datasets.save_to_disk(PROJECT_DIR + 'datasets/' + TARGET_CORPUS + '-' + UNDERSAMPLE_FACTOR + '-typed-entity-marked-flow')

df['Label'].value_counts().sum() - df['Label'].value_counts()['non-edge'] - GLOBAL_EDGE_COUNT <= 1