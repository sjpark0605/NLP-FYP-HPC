# GPU job script example.
#$ -S /bin/bash
#$ -l h_rt=36:00:0
#$ -l tmem=16G
#$ -wd /cluster/project2/COMP0029_17022125/NLP-FYP-HPC
#$ -j y
#$ -l gpu=true
#$ -pe gpu 1
#$ -R y
#$ -o /cluster/project2/COMP0029_17022125/NLP-FYP-HPC/logs/unweighted
#$ -m beas

target=$arg1
undersample=$arg2
epochs=$arg3

source /share/apps/source_files/python/python-3.9.5.source
source /share/apps/source_files/cuda/cuda-11.0.source
source /cluster/project2/COMP0029_17022125/NLP-FYP-HPC/.venv/bin/activate
python3 /cluster/project2/COMP0029_17022125/NLP-FYP-HPC/directional-input/directional_input_flow_graph_data_processing.py --t "$target" --us "$undersample"
python3 /cluster/project2/COMP0029_17022125/NLP-FYP-HPC/directional-input/directional_input_flow_graph_training_loop.py  --t "$target" --us "$undersample" --epochs "$epochs"
hostname
date