#!/bin/bash

# Parse command line arguments
while getopts "t:u:e:" opt; do
  case $opt in
    t) target="$OPTARG" ;;
    u) undersample="$OPTARG" ;;
    e) epochs="$OPTARG" ;;
    *) exit 1 ;;
  esac
done

# Check if name and age are provided
if [[ -z "$target" || -z "$undersample" || -z "$epochs" ]]; then
  echo "Error: Corpus Name (-t), Undersampling Rate (-u), and Epochs (-e) are required." >&2
  exit 1
fi

di_job_name="${target}_D-I_${undersample}_US_Weighted_Flow_Training_with_${epochs}_Epochs"
dl_job_name="${target}_D-L_${undersample}_US_Weighted_Flow_Training_with_${epochs}_Epochs"
em_job_name="${target}_E-M_${undersample}_US_Weighted_Flow_Training_with_${epochs}_Epochs"
tm_job_name="${target}_T-M_${undersample}_US_Weighted_Flow_Training_with_${epochs}_Epochs"

# Print the values of the arguments to the console
qsub -N ${di_job_name} -v arg1="$target",arg2="$undersample",arg3="$epochs" /cluster/project2/COMP0029_17022125/directional-input/train_weighted_di_flow.qsub.sh 
qsub -N ${dl_job_name} -v arg1="$target",arg2="$undersample",arg3="$epochs" /cluster/project2/COMP0029_17022125/directional-label/train_weighted_dl_flow.qsub.sh 
qsub -N ${em_job_name} -v arg1="$target",arg2="$undersample",arg3="$epochs" /cluster/project2/COMP0029_17022125/entity-marker/train_weighted_em_flow.qsub.sh 
qsub -N ${tm_job_name} -v arg1="$target",arg2="$undersample",arg3="$epochs" /cluster/project2/COMP0029_17022125/typed-entity-marker/train_weighted_tm_flow.qsub.sh 