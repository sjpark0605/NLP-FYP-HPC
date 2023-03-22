# GPU job script example.
#$ -S /bin/bash
#$ -l h_rt=2:00:0
#$ -l tmem=4G
#$ -wd /home/sejipark/NLP-FYP-HPC
#$ -j y
#$ -N Directed_Input_Training_Submission_R200
#$ -l gpu=true,gpu_type=rtx2080ti
#$ -pe gpu 1
#$ -R y
#$ -m beas
# Commands to be executed follow.
source /share/apps/source_files/python/python-3.10.0.source
source /home/sejipark/NLP-FYP-HPC/.venv/bin/activate
python3 /home/sejipark/NLP-FYP-HPC/directional-input/directional_input_flow_graph_data_processing.py --t r-200 --us 0.9
python3 /home/sejipark/NLP-FYP-HPC/directional-input/directional_input_flow_graph_training_loop.py  --t r-200 --epochs 10
hostname
date
/home/sejipark/test