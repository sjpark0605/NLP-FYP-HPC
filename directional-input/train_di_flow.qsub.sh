# GPU job script example.
#$ -S /bin/bash
#$ -l h_rt=36:00:0
#$ -l tmem=8G
#$ -wd /home/sejipark/NLP-FYP-HPC
#$ -j y
#$ -l gpu=true,gpu_type=rtx2080ti
#$ -pe gpu 1
#$ -R y
#$ -m beas
# Commands to be executed follow.

target=$arg1
undersample=$arg2
epochs=$arg3

source /share/apps/source_files/python/python-3.10.0.source
source /home/sejipark/NLP-FYP-HPC/.venv/bin/activate
python3 /home/sejipark/NLP-FYP-HPC/directional-input/directional_input_flow_graph_data_processing.py --t "$target" --us "$undersample"
python3 /home/sejipark/NLP-FYP-HPC/directional-input/directional_input_flow_graph_training_loop.py  --t "$target" --epochs "$epochs"
hostname
date
/home/sejipark/test