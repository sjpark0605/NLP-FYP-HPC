#!/bin/bash

# Parse command line arguments
while getopts "t:e:" opt; do
  case $opt in
    t) target="$OPTARG" ;;
    e) epochs="$OPTARG" ;;
    *) exit 1 ;;
  esac
done

# Check if name and age are provided
if [[ -z "$target" || -z "$epochs" ]]; then
  echo "Error: Both corpus name (-t) and epochs (-e) are required." >&2
  exit 1
fi

job_name="NER Training with $target"

# Print the values of the arguments to the console
qsub -N ${job_name} /home/sejipark/NLP-FYP-HPC/ner/train_ner.qsub.sh -v arg1=target arg2=epochs