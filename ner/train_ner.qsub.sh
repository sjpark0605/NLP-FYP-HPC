# GPU job script example.
#$ -S /bin/bash
#$ -l h_rt=2:00:0
#$ -l tmem=4G
#$ -wd /cluster/project2/COMP0029_17022125
#$ -j y
#$ -l gpu=true
#$ -pe gpu 1
#$ -R y
#$ -m beas
# Commands to be executed follow.

target=$arg1
epochs=$arg2

echo $arg1
echo $arg2

source /share/apps/source_files/python/python-3.9.5.source
source /share/apps/source_files/cuda/cuda-11.0.source
source /cluster/project2/COMP0029_17022125/.venv/bin/activate
python3 /cluster/project2/COMP0029_17022125/ner/ner_data_processing.py --t "$target"
python3 /cluster/project2/COMP0029_17022125/ner/ner_training_loop.py --t "$target" --epochs "$epochs"
hostname
date