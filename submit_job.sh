#!/bin/sh
#
# Replace <ACCOUNT> with your account name before submitting.
#
#SBATCH --account=dsi     # The account name for the job.
#SBATCH --job-name=arxiv_test    # The job name.
#SBATCH -c 1                     # The number of cpu cores to use.
#SBATCH --time=24:00:00              # The time the job will take to run (here, 1 min)
#SBATCH --mem-per-cpu=64gb        # The memory the job will use per cpu core.
#SBATCH -o ev_%A_%a.out
#SBATCH -e ev_%A_%a.err
#SBATCH --array=1-10


module load anaconda/3-5.1
source activate arxivlab
echo "SLURM_ARRAY_TASK_ID: " ${SLURM_ARRAY_TASK_ID}
python3 generate_mml.py --initial --singular /local/hoptex/initial ${SLURM_ARRAY_TASK_ID}

#End of script
