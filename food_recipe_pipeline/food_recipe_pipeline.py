# -*- coding: utf-8 -*-
"""Food Recipe Pipeline.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1wKxEcqJGMdfamcYIU8f7HXeO8r12IysY
"""

# Commented out IPython magic to ensure Python compatibility.
# %%capture
# !pip install transformers[sentencepiece]

import pickle

import matplotlib.pyplot as plt
import networkx as nx
import nltk
import pydot
import torch
from IPython.display import Image
from transformers import (
    AutoModelForSequenceClassification,
    AutoModelForTokenClassification,
    AutoTokenizer,
    BertTokenizer,
)

PROJECT_DIR = "/cluster/project2/COMP0029_17022125/NLP-FYP-HPC/"

device = torch.device("cpu")

if torch.cuda.is_available():
    device = torch.device("cuda")

ner_model = AutoModelForTokenClassification.from_pretrained(
    PROJECT_DIR + "saved_models/ner"
).to(device)
ner_tokenizer = AutoTokenizer.from_pretrained("bert-base-cased")

ner_id2label = ner_model.config.id2label


def obtain_ner_tags(sentences):
    word_dict, ner_dict = {}, {}

    for i, sentence in enumerate(sentences):
        input = ner_tokenizer.encode_plus(
            sentence, truncation=True, max_length=128, return_tensors="pt"
        ).to(device)

        tokens = ner_tokenizer.convert_ids_to_tokens(input["input_ids"].squeeze())
        logits = ner_model(**input).get("logits")
        predictions = logits.argmax(dim=-1).squeeze()

        joined_words, joined_labels = [], []

        for token, prediction in zip(tokens, predictions):
            if token.startswith("##"):
                joined_words[-1] += token.replace("##", "")
            elif token != "[CLS]" and token != "[SEP]":
                joined_words.append(token)
                joined_labels.append(ner_id2label[prediction.item()])

        for j, (word, label) in enumerate(zip(joined_words, joined_labels)):
            word_dict[(i, j)] = word
            ner_dict[(i, j)] = label

    return word_dict, ner_dict


nltk.download("punkt")


def split_text_into_sentences(text):
    sentences = nltk.sent_tokenize(text)
    return sentences


flow_model = AutoModelForSequenceClassification.from_pretrained(
    PROJECT_DIR + "saved_models/entity-marker"
).to(device)
flow_tokenizer = tokenizer = BertTokenizer.from_pretrained(
    PROJECT_DIR + "tokenizers/entity-marker"
)

flow_id2label = flow_model.config.id2label

with open(PROJECT_DIR + "relation_set.pickle", "rb") as relation_set_file:
    RELATION_SET = pickle.load(relation_set_file)


def construct_entity_pairs(ner_dict):
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


def obtain_flow_edges(word_dict, ner_dict, phrase_dict, entity_pairs):
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


def food_recipe_to_flow_graph(text):
    sentences = split_text_into_sentences(text)
    word_dict, ner_dict = obtain_ner_tags(sentences)
    print(word_dict)
    print(ner_dict)
    entity_pairs = construct_entity_pairs(ner_dict)
    phrase_dict = construct_phrase_dict(word_dict, ner_dict)

    edges = obtain_flow_edges(word_dict, ner_dict, phrase_dict, entity_pairs)
    nodes = set()

    for edge in edges:
        node1 = (edge[0][0], edge[1][0], edge[2][0])
        node2 = (edge[0][1], edge[1][1], edge[2][1])

        nodes.add(node1)
        nodes.add(node2)

    return nodes, edges


def construct_graph(nodes, edges):
    flow_graph = nx.DiGraph()

    for node in nodes:
        flow_graph.add_node(
            str(node[0])
            + " "
            + node[1]
            + " ["
            + node[2].replace("-B", "").replace("-I", "")
            + "]"
        )

    for edge in edges:
        node1 = str(edge[0][0]) + " " + edge[1][0]
        node2 = str(edge[0][1]) + " " + edge[1][1]

        if edge[3].endswith(":LR"):
            flow_graph.add_edge(node1, node2, label=edge[3].replace(":LR", ""))
        else:
            flow_graph.add_edge(node2, node1, label=edge[3].replace(":RL", ""))

    return flow_graph


node_shape = {"F": "ellipse", "T": "hexagon", "Ac": "rectangle", "Ac2": "rectangle"}


def get_node_style(ner_tag):
    shape, color, style = "ellipse", "black", "dashed"

    if ner_tag == "T" or ner_tag == "Ac" or ner_tag == "Ac2":
        color = "red"

    if ner_tag in node_shape:
        shape = node_shape[ner_tag]
        style = "solid"

    return shape, color, style


def visualize_graph(nodes, edges):
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

    graph.write_png("flow_graph.png")


text = "Put 500mL of water in a pot on high heat. Cook cook the instant noodles in the boiling water for 5 minutes. Mix the flavouring packet with the noodles and serve."
nodes, edges = food_recipe_to_flow_graph(text)

# flow_graph = construct_graph(nodes, edges)
# cycles = list(nx.simple_cycles(flow_graph))
# print(cycles)

# visualize_graph(nodes, edges)
# Image(filename="flow_graph.png")
