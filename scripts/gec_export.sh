#!/bin/bash
#set -o xtrace
#set -o verbose
set -o errexit
set -o nounset
set -o pipefail
set -o errtrace

WD=$(dirname $(readlink -e $0))
VOCAB_DIR="$(readlink -e $WD/../t2t_data_dir)"
USR_DIR="$(readlink -e $WD/../t2t_usr_dir)"
MODEL_DIR="$1"
LANG=$(basename "$MODEL_DIR")

#export LD_LIBRARY_PATH=/opt/cuda/9.0/lib64/:/opt/cuda/9.0/cudnn/7.0/lib64/
source /home/okosarko/venv/gpu-tf16/bin/activate
#export PYTHONPATH=/home/popel/work/tensor2tensor/v/t$VERSION
#export PATH=/home/popel/work/tensor2tensor/v/t$VERSION/tensor2tensor/bin:$PATH

time t2t-exporter \
    --model=transformer \
    --hparams_set=transformer_big_single_gpu \
    --problem="artificial_errors_$LANG" \
    --t2t_usr_dir="$USR_DIR" \
    --data_dir="$VOCAB_DIR" \
    --output_dir="$MODEL_DIR" \
    --decode_hparams="beam_size=4,alpha=0.6"
