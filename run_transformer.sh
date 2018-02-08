#!/bin/bash
echo "Started" > /tmp/debug.log
source /home/varis/tensorflow-virtualenv/bin/activate
export PYTHONPATH=/home/varis/tensor2tensor-1.2.9/
cd /home/varis/
bash sample.command
