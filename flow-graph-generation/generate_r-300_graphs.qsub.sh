# GPU job script example.
#$ -S /bin/bash
#$ -l h_rt=4:00:0
#$ -l tmem=4G
#$ -wd /cluster/project2/COMP0029_17022125/NLP-FYP-HPC
#$ -j y
#$ -l gpu=true
#$ -pe gpu 1
#$ -R y
#$ -o /cluster/project2/COMP0029_17022125/NLP-FYP-HPC/logs/generate_flow
#$ -m beas
# Commands to be executed follow.

target=$arg1
epochs=$arg2

echo $arg1
echo $arg2

source /share/apps/source_files/python/python-3.9.5.source
source /share/apps/source_files/cuda/cuda-11.0.source
source /cluster/project2/COMP0029_17022125/NLP-FYP-HPC/.venv/bin/activate
python3 /cluster/project2/COMP0029_17022125/NLP-FYP-HPC/flow-graph-generation/generate_r-300_flow_graphs.py
hostname
date