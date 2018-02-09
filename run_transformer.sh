#!/bin/bash
echo "Started" > /tmp/debug.log
#INPUT=/home/varis/test.in
INPUT=$1
OUTPUT=$(basename $INPUT)
cd /home/okosarko/scripts
cp $INPUT ${INPUT}_1
./split-sentences.pl < ${INPUT}_1 > $INPUT
source /home/varis/tensorflow-virtualenv/bin/activate
export PYTHONPATH=/home/varis/tensor2tensor-1.2.9/
cd /home/varis/
tensor2tensor-1.2.9/tensor2tensor/bin/t2t-decoder \
	--t2t_usr_dir=~varis/t2t_usr_dir/ \
	--data_dir=~varis/t2t_data_dir/ \
	--model=transformer \
	--hparams_set=transformer_big_single_gpu \
	--output_dir=~varis/t2t-model \
	--problems=translate_encs_wmt_czeng57m32k \
	--decode_hparams=beam_size=4,alpha=0.6 \
	--train_steps=0 \
	--eval_steps=0 \
	--decode_from_file=$INPUT \
        --decode_to_file=/tmp/$OUTPUT
wait
while [ ! -f "/tmp/${OUTPUT}.transformer.transformer_big_single_gpu.translate_encs_wmt_czeng57m32k.beam4.alpha0.6.decodes" ]; do
   sleep 10
done
