#!/bin/bash

#SBATCH --job-name={jobid}
#SBATCH --output={jobid}_log.log
#SBATCH --cpus-per-task=1
#SBATCH --time=16:00:00
#SBATCH --mem=30G

python program.py {props}

