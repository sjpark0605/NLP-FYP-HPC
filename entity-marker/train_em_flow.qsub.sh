# GPU job script example.
#$ -S /bin/bash
#$ -l h_rt=24:00:0
#$ -l tmem=16G
#$ -wd /home/sejipark/NLP-FYP-HPC
#$ -j y
#$ -l gpu=true
#$ -pe gpu 1
#$ -R y
#$ -m beas
# Commands to be executed follow.

target=$arg1
undersample=$arg2
epochs=$arg3

source /share/apps/source_files/python/python-3.10.0.source
source /home/sejipark/NLP-FYP-HPC/.venv/bin/activate
python3 /home/sejipark/NLP-FYP-HPC/entity-marker/entity_marker_flow_graph_data_processing.py --t "$target" --us "$undersample"
python3 /home/sejipark/NLP-FYP-HPC/entity-marker/entity_marker_flow_graph_training_loop.py  --t "$target" --us "$undersample" --epochs "$epochs"
hostname
date
/home/sejipark/test