#!/bin/bash

mkdir -p logs/unweighted
mkdir -p logs/weighted

arguments1=("r-100" "r-200" "r-300")
arguments2=(0.0 0.5 0.25 0.1)

for arg1 in "${arguments1[@]}"
do
  for arg2 in "${arguments2[@]}"
  do
    ./submit_flow_jobs.sh -t "$arg1" -u "$arg2" -e 6
    # ./submit_flow_jobs.sh -t "$arg1" -u "$arg2" -e 6 --weighted
  done
done