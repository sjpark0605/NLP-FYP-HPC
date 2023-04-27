#!/bin/bash

mkdir -p logs/ner

arguments1=("r-100" "r-200" "r-300")

for arg1 in "${arguments1[@]}"
do
  ./submit_ner_job.sh -t "$arg1" -e 6
done