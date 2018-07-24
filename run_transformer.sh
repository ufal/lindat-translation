#!/bin/bash
echo "`date -Ins`: Started" >> /tmp/debug.log
#INPUT=/home/varis/test.in
INPUT=$1
echo "`date -Ins`: INPUT=$INPUT" >> /tmp/debug.log
OUTPUT=$2
echo "`date -Ins`: OUTPUT=$OUTPUT" >> /tmp/debug.log
LANG_PAIR=${3:-"en-cs"}
echo "`date -Ins`: LANG_PAIR=$LANG_PAIR" >> /tmp/debug.log
cd /home/okosarko/scripts
cp $INPUT ${INPUT}_1
./split-sentences.pl -l ${LANG_PAIR%-*} < ${INPUT}_1 > $INPUT
echo "`date -Ins`: ./split-sentences.pl -l ${LANG_PAIR%-*} < ${INPUT}_1 > $INPUT" >> /tmp/debug.log
source /home/varis/tensor2tensor-venv-1.4.2/bin/activate
export PYTHONPATH=/home/varis/tensor2tensor-1.4.2/
cd /home/varis/
tensor2tensor-1.4.2/tensor2tensor/bin/t2t-decoder \
	--t2t_usr_dir=~varis/t2t_usr_dir/ \
	--data_dir=~varis/t2t_data_dir/ \
	--model=transformer \
	--hparams_set=transformer_big_single_gpu \
	--output_dir=~varis/t2t-model.$LANG_PAIR \
	--problems=translate_encs_wmt_czeng57m32k \
	--decode_hparams=beam_size=4,alpha=1.0 \
	--train_steps=0 \
	--eval_steps=0 \
	--decode_from_file=$INPUT \
        --decode_to_file=$OUTPUT
wait
