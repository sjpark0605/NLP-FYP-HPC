#!/bin/bash

mkdir -p logs/unweighted
mkdir -p logs/weighted

arguments2=(0.9 0.75 0.5 0.0)

for arg2 in "${arguments2[@]}"
do
  ./submit_flow_jobs.sh -t "r-300" -u "$arg2" -e 6
  ./submit_weighted_flow_jobs.sh -t "r-300" -u "$arg2" -e 6
done