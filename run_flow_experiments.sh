#!/bin/bash

mkdir -p logs/unweighted
mkdir -p logs/weighted

arguments1=("r-300" "r-200" "r-100")
arguments2=(0.9 0.75 0.5 0.0)

for arg1 in "${arguments1[@]}"
do
  for arg2 in "${arguments2[@]}"
  do
    ./submit_weighted_flow_jobs.sh -t "$arg1" -u "$arg2" -e 6
  done
done