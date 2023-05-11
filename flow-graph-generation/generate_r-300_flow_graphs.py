# -*- coding: utf-8 -*-
"""Analysis of Food Recipe Pipeline.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/10XyZkE4viWPaXKJG-utD7U6Er8PrIm9J
"""

import glob
import os
from pathlib import Path

import pydot
import torch
from tqdm import tqdm
from transformers import (
    AutoModelForSequenceClassification,
    AutoModelForTokenClassification,
    AutoTokenizer,
)

device = torch.device("cpu")

if torch.cuda.is_available():
    device = torch.device("cuda")

PROJECT_DIR = "/cluster/project2/COMP0029_17022125/NLP-FYP-HPC/"

NER_FILES, FLOW_FILES = [], []

for corpus in ["r-100", "r-200"]:
    NER_FILES += glob.glob(PROJECT_DIR + corpus + "/*.list")
    FLOW_FILES += glob.glob(PROJECT_DIR + corpus + "/*.flow")

NER_FILES.sort()
FLOW_FILES.sort()

ner_model = AutoModelForTokenClassification.from_pretrained(
    PROJECT_DIR + "saved-models/ner-model"
).to(device)
ner_tokenizer = AutoTokenizer.from_pretrained("bert-base-cased")

ner_id2label = ner_model.config.id2label


def split_into_sentences(ner_lines):
    sentences, sentence, keys_list, keys = [], [], [], []

    for line in ner_lines:
        items = line.strip().split(" ")
        position = (int(items[0]), int(items[1]), int(items[2]))
        word, pos = items[3], items[4]

        sentence.append(word)
        keys.append(position)

        if pos == ".":
            sentences.append(sentence)
            keys_list.append(keys)
            sentence, keys = [], []

    return sentences, keys_list


def obtain_predicted_ner_tags(sentences, keys_list):
    word_dict, ner_dict = {}, {}

    for sentence, keys in zip(sentences, keys_list):
        input = ner_tokenizer.encode_plus(
            sentence,
            truncation=True,
            is_split_into_words=True,
            max_length=128,
            return_tensors="pt",
        ).to(device)
        tokens, word_ids = input.tokens(), input.word_ids()

        logits = ner_model(**input).get("logits")
        predictions = logits.argmax(dim=-1).squeeze()

        untokenized_sentence, labels = [], []

        prev_word_id = None
        for token, word_id, prediction in zip(tokens, word_ids, predictions):
            if word_id != None:
                if prev_word_id != word_id:
                    untokenized_sentence.append(token)
                    labels.append(ner_id2label[prediction.item()])
                    prev_word_id = word_id
                else:
                    untokenized_sentence[-1] += token.replace("##", "")

        for word, label, key in zip(sentence, labels, keys):
            word_dict[key] = word
            ner_dict[key] = label

    return word_dict, ner_dict


def obtain_true_ner_tags(ner_lines):
    word_dict, ner_dict = {}, {}

    for line in ner_lines:
        items = line.strip().split(" ")

        key = (int(items[0]), int(items[1]), int(items[2]))
        word, ner_tag = items[3], items[5]

        word_dict[key] = word
        ner_dict[key] = ner_tag

    return word_dict, ner_dict


flow_model = AutoModelForSequenceClassification.from_pretrained(
    PROJECT_DIR + "saved-models/entity-marker-model"
).to(device)
flow_tokenizer = AutoTokenizer.from_pretrained(PROJECT_DIR + "tokenizers/entity-marker")

flow_id2label = flow_model.config.id2label

import pickle

with open(PROJECT_DIR + "r-300-relation_set.pickle", "rb") as relation_set_file:
    RELATION_SET = pickle.load(relation_set_file)


def construct_predicted_entity_pairs(ner_dict):
    entity_pairs = []

    ner_keys = list(ner_dict.keys())

    for i in range(len(ner_keys)):
        for j in range(i + 1, len(ner_keys)):
            pair1 = ner_dict[ner_keys[i]] + "->" + ner_dict[ner_keys[j]]
            pair2 = ner_dict[ner_keys[j]] + "->" + ner_dict[ner_keys[i]]

            if pair1 in RELATION_SET or pair2 in RELATION_SET:
                entity_pairs.append((ner_keys[i], ner_keys[j]))

    return entity_pairs


def construct_sentence(word_dict, ner_dict, sentence_index, target_positions):
    word_keys = sorted(list(word_dict.keys()))

    first_word = True

    sentence = ""

    marking = -1
    marking_ner_tag = None

    for word_key in word_keys:
        word = word_dict[word_key]
        word_added = False

        if sentence_index == word_key[0]:
            if marking != -1:
                if marking_ner_tag.replace("-B", "-I") != ner_dict[word_key]:
                    sentence += " </e" + str(marking) + ">"
                    marking, marking_ner_tag = -1, None

            if not first_word:
                sentence += " "
            first_word = False

            for i, target_position in enumerate(target_positions):
                if word_key == target_position:
                    marking, marking_ner_tag = i + 1, ner_dict[word_key]

                    sentence += "<e" + str(marking) + "> " + word
                    word_added = True

            if not word_added:
                sentence += word

    if marking != -1:
        sentence += " </e" + str(marking) + ">"

    return sentence


def construct_sentence_pair(word_dict, ner_dict, entity_pair):
    first_sentence = construct_sentence(
        word_dict, ner_dict, entity_pair[0][0], entity_pair
    )
    second_sentence = construct_sentence(
        word_dict, ner_dict, entity_pair[1][0], entity_pair
    )

    if first_sentence == second_sentence:
        return first_sentence, None
    return first_sentence, second_sentence


def tokenize_sentence_pair(first_sentence, second_sentence):
    if second_sentence is None:
        return flow_tokenizer(
            first_sentence,
            add_special_tokens=True,
            max_length=128,
            padding="max_length",
            return_tensors="pt",
        )
    return flow_tokenizer(
        first_sentence,
        second_sentence,
        add_special_tokens=True,
        max_length=128,
        padding="max_length",
        return_tensors="pt",
    )


def construct_true_entity_pairs_with_labels(flow_lines):
    entity_pairs, labels = [], []

    for line in flow_lines:
        items = line.strip().split(" ")

        source_key = (int(items[0]), int(items[1]), int(items[2]))
        dest_key = (int(items[4]), int(items[5]), int(items[6]))
        label = items[3]

        entity_pairs.append((source_key, dest_key))
        labels.append(label)

    return entity_pairs, labels


def construct_phrase_dict(word_dict, ner_dict):
    phrase_dict = {}

    word_keys = sorted(list(word_dict.keys()))
    previous_key = None

    for word_key in word_keys:
        if (
            previous_key != None
            and ner_dict[previous_key].replace("-B", "-I") == ner_dict[word_key]
        ):
            phrase_dict[previous_key] += " " + word_dict[word_key]
        else:
            phrase_dict[word_key] = word_dict[word_key]
            previous_key = word_key

    return phrase_dict


def obtain_predicted_flow_edges(word_dict, ner_dict, phrase_dict, entity_pairs):
    edges = []

    for entity_pair in entity_pairs:
        first_sentence, second_sentence = construct_sentence_pair(
            word_dict, ner_dict, entity_pair
        )
        input = tokenize_sentence_pair(first_sentence, second_sentence).to(device)
        logits = flow_model(**input).get("logits")
        label = flow_id2label[logits.argmax(dim=-1).squeeze().item()]

        if label != "non-edge":
            edges.append(
                (
                    entity_pair,
                    (phrase_dict[entity_pair[0]], phrase_dict[entity_pair[1]]),
                    (ner_dict[entity_pair[0]], ner_dict[entity_pair[1]]),
                    label,
                )
            )

    return edges


def obtain_true_flow_edges(ner_dict, phrase_dict, entity_pairs, labels):
    edges = []

    for entity_pair, label in zip(entity_pairs, labels):
        edges.append(
            (
                entity_pair,
                (phrase_dict[entity_pair[0]], phrase_dict[entity_pair[1]]),
                (ner_dict[entity_pair[0]], ner_dict[entity_pair[1]]),
                label,
            )
        )

    return edges


def food_recipe_to_predicted_flow_graph(ner_lines):
    sentences, keys_list = split_into_sentences(ner_lines)
    word_dict, ner_dict = obtain_predicted_ner_tags(sentences, keys_list)
    entity_pairs = construct_predicted_entity_pairs(ner_dict)
    phrase_dict = construct_phrase_dict(word_dict, ner_dict)

    edges = obtain_predicted_flow_edges(word_dict, ner_dict, phrase_dict, entity_pairs)
    nodes = set()

    for edge in edges:
        node1 = (edge[0][0], edge[1][0], edge[2][0])
        node2 = (edge[0][1], edge[1][1], edge[2][1])

        nodes.add(node1)
        nodes.add(node2)

    return nodes, edges


def food_recipe_to_true_flow_graph(ner_lines, flow_lines):
    word_dict, ner_dict = obtain_true_ner_tags(ner_lines)
    entity_pairs, labels = construct_true_entity_pairs_with_labels(flow_lines)
    phrase_dict = construct_phrase_dict(word_dict, ner_dict)

    edges = obtain_true_flow_edges(ner_dict, phrase_dict, entity_pairs, labels)
    nodes = set()

    for edge in edges:
        node1 = (edge[0][0], edge[1][0], edge[2][0])
        node2 = (edge[0][1], edge[1][1], edge[2][1])

        nodes.add(node1)
        nodes.add(node2)

    return nodes, edges


node_shape = {"F": "ellipse", "T": "hexagon", "Ac": "rectangle", "Ac2": "rectangle"}


def get_node_style(ner_tag):
    shape, color, style = "ellipse", "black", "dashed"

    if ner_tag == "T" or ner_tag == "Ac" or ner_tag == "Ac2":
        color = "red"

    if ner_tag in node_shape:
        shape = node_shape[ner_tag]
        style = "solid"

    return shape, color, style


def generate_predicted_graph(nodes, edges, dest_folder):
    graph = pydot.Dot(graph_type="digraph")

    node_dict = {}

    for node in nodes:
        ner_tag = node[2].replace("-B", "").replace("-I", "")
        shape, color, style = get_node_style(ner_tag)

        key = str(node[0]) + " " + node[1] + " [" + ner_tag + "]"
        pydot_node = pydot.Node(key.strip(), shape=shape, color=color, style=style)
        graph.add_node(pydot_node)
        node_dict[key] = pydot_node

    for edge in edges:
        node1_key = (
            str(edge[0][0])
            + " "
            + edge[1][0]
            + " ["
            + edge[2][0].replace("-B", "").replace("-I", "")
            + "]"
        )
        node2_key = (
            str(edge[0][1])
            + " "
            + edge[1][1]
            + " ["
            + edge[2][1].replace("-B", "").replace("-I", "")
            + "]"
        )
        node1, node2 = node_dict[node1_key], node_dict[node2_key]

        if edge[3].endswith(":LR"):
            pydot_edge = pydot.Edge(
                node1, node2, label=edge[3].strip().replace(":LR", "")
            )
            graph.add_edge(pydot_edge)
        else:
            pydot_edge = pydot.Edge(
                node2, node1, label=edge[3].strip().replace(":RL", "")
            )
            graph.add_edge(pydot_edge)

    graph.write_png(dest_folder + "/predicted_flow_graph.png")


def generate_true_graph(nodes, edges, dest_folder):
    graph = pydot.Dot(graph_type="digraph")

    node_dict = {}

    for node in nodes:
        ner_tag = node[2].replace("-B", "").replace("-I", "")
        shape, color, style = get_node_style(ner_tag)

        key = str(node[0]) + " " + node[1] + " [" + ner_tag + "]"
        pydot_node = pydot.Node(key.strip(), shape=shape, color=color, style=style)
        graph.add_node(pydot_node)
        node_dict[key] = pydot_node

    for edge in edges:
        node1_key = (
            str(edge[0][0])
            + " "
            + edge[1][0]
            + " ["
            + edge[2][0].replace("-B", "").replace("-I", "")
            + "]"
        )
        node2_key = (
            str(edge[0][1])
            + " "
            + edge[1][1]
            + " ["
            + edge[2][1].replace("-B", "").replace("-I", "")
            + "]"
        )
        node1, node2 = node_dict[node1_key], node_dict[node2_key]

        pydot_edge = pydot.Edge(node1, node2, label=edge[3])
        graph.add_edge(pydot_edge)

    graph.write_png(dest_folder + "true_flow_graph.png")


for ner_file, flow_file in tqdm(
    zip(NER_FILES, FLOW_FILES), desc="Generating Flow Graphs", position=0
):
    ner_data, flow_data = open(ner_file, "r", encoding="utf-8"), open(
        flow_file, "r", encoding="utf-8"
    )
    ner_lines, flow_lines = ner_data.readlines(), flow_data.readlines()

    filename_without_extension = Path(ner_file).stem
    dest_folder = (
        PROJECT_DIR
        + "outputs/generated_flow_graphs/"
        + filename_without_extension
        + "/"
    )

    if not os.path.exists(dest_folder):
        os.makedirs(dest_folder)

    predicted_nodes, predicted_edges = food_recipe_to_predicted_flow_graph(ner_lines)
    true_nodes, true_edges = food_recipe_to_true_flow_graph(ner_lines, flow_lines)

    with open(dest_folder + "predicted_flow_graph.pkl", "wb") as pred_f:
        pickle.dump((predicted_nodes, predicted_edges), pred_f)

    with open(dest_folder + "true_flow_graph.pkl", "wb") as true_f:
        pickle.dump((true_nodes, true_edges), true_f)

    ner_data.close()
    flow_data.close()
    pred_f.close()
    true_f.close()

    generate_predicted_graph(predicted_nodes, predicted_edges, dest_folder)
    generate_true_graph(true_nodes, true_edges, dest_folder)
