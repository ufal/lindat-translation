#!/bin/bash
echo "Started" > /tmp/debug.log
#INPUT=/home/varis/test.in
INPUT=$1
OUTPUT=$2
LANG_PAIR=${3:-"en-cs"}
cd /home/okosarko/scripts
cp $INPUT ${INPUT}_1
./split-sentences.pl -l ${LANG_PAIR%-*} < ${INPUT}_1 > $INPUT
source /home/varis/tensorflow-virtualenv/bin/activate
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
