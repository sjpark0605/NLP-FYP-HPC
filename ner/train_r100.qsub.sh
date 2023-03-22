# GPU job script example.
#$ -S /bin/bash
#$ -l h_rt=2:00:0
#$ -l tmem=4G
#$ -wd /home/sejipark/NLP-FYP-HPC
#$ -j y
#$ -N NER_Training_Submission_R100
#$ -l gpu=true,gpu_type=gtx1080ti
#$ -pe gpu 1
#$ -R y
#$ -m beas
# Commands to be executed follow.
source /share/apps/source_files/python/python-3.10.0.source
source /home/sejipark/NLP-FYP-HPC/.venv/bin/activate
python3 /home/sejipark/NLP-FYP-HPC/ner/ner_data_processing.py --t r-100
python3 /home/sejipark/NLP-FYP-HPC/ner/ner_training_loop.py --t r-100 --epochs 10
hostname
date
/home/sejipark/test