# GPU job script example.
#$ -S /bin/bash
#$ -l h_rt=36:00:0
#$ -l tmem=16G
#$ -wd /home/sejipark/NLP-FYP-HPC
#$ -j y
#$ -l gpu=true,gpu_type=rtx2080ti
#$ -pe gpu 1
#$ -R y
#$ -o /home/sejipark/NLP-FYP-HPC/logs/weighted
#$ -m beas
# Commands to be executed follow.

target=$arg1
undersample=$arg2
epochs=$arg3

source /share/apps/source_files/python/python-3.9.5.source
source /share/apps/source_files/cuda/cuda-11.0.source
source /home/sejipark/NLP-FYP-HPC/.venv/bin/activate
python3 /home/sejipark/NLP-FYP-HPC/directional-label/directional_label_flow_graph_data_processing.py --t "$target" --us "$undersample"
python3 /home/sejipark/NLP-FYP-HPC/directional-label/directional_label_flow_graph_training_loop.py  --t "$target" --us "$undersample" --epochs "$epochs" --weighted
hostname
date
/home/sejipark/test