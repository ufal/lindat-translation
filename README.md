# transformer_frontend
A simple flask based ui in front of tensorflow serving.

In our setup the flask app runs on a machine called `transformer` and tensorflow serving on another machine called `t2t-transformer`.

## Install

### To install and run frontend
```
git clone --recurse-submodules git@github.com:ufal/transformer_frontend
pip install -r requirements.txt
gunicorn -t 500 -k sync -w 12 -b 0.0.0.0:5000 uwsgi:app
```
systemd configs are provided in order to run as a system service, sample docker (see [Dockerfile](./Dockerfile), [docker-compose.yml](./docker-compose.yml)) configuration is provided for testing. Both need tweaking.

### Serving
The easiest but probably suboptimal (you likely want to compile yourself) way is to follow https://www.tensorflow.org/serving/setup and get a .deb package.
There's also a docker image, we use that in the sample setup (see [docker-compose.yml](./docker-compose.yml)), but you'll need to provide a model and set a proper path to it

#### Serving build
The nvidia driver version we use is 440.33.01

The following describes how I've managed to build version 2.1.0 (2.3.0 gives SIGSEGV when you send any data, 2.2.0 had some strange startup times and didn't respond on REST-api)

The official "documentation" is https://github.com/tensorflow/serving/blob/2.1.0/tensorflow_serving/tools/docker/Dockerfile.devel-gpu

There is a compatibility matrix at https://www.tensorflow.org/install/source#gpu it diverges from what gets pushed onto dockerhub (https://hub.docker.com/r/tensorflow/serving/tags)

install bazelisk from https://github.com/bazelbuild/bazelisk
```
export USE_BAZEL_VERSION=0.24.1
```
version `2.1.0` is built from `git checkout d83512c6` of (https://github.com/tensorflow/serving)
The python virtualenv contains the following packages, mind especially the numpy version
```
certifi==2020.6.20
chardet==3.0.4
future==0.18.2
grpcio==1.32.0
h5py==2.10.0
idna==2.10
Keras-Applications==1.0.8
Keras-Preprocessing==1.1.2
mock==4.0.2
numpy==1.18.5
pkg-resources==0.0.0
requests==2.24.0
six==1.15.0
urllib3==1.25.10
```
The following command sets the necessary variables and paths to run the build
```
TMP=/tmp CUDA_VISIBLE_DEVICES=0 TF_NCCL_VERSION= TF_NEED_CUDA=1 TF_NEED_TENSORRT=1 TENSORRT_INSTALL_PATH=/home/okosarko/junk/TensorRT-5.1.5.0/ TF_CUDA_VERSION=10.0 TF_CUDNN_VERSION=7 CUDNN_INSTALL_PATH=/opt/cuda/10.0/cudnn/7.6/ LD_LIBRARY_PATH=/opt/cuda/10.0/lib64/stubs:/opt/cuda/10.0/extras/CUPTI/lib64:/opt/cuda/10.0/lib64:/opt/cuda/10.0/cudnn/7.6/lib64/:/usr/include/x86_64-linux-gnu:/usr/lib/x86_64-linux-gnu PYTHONPATH=/mnt/transformers-shared/venv/lib/python3.6/site-packages bazelisk build --color=yes --curses=yes --config=cuda --config=nativeopt --config=release --copt=-fPIC --verbose_failures --output_filter=DONT_MATCH_ANYTHING --action_env PYTHON_BIN_PATH=/mnt/transformers-shared/venv/bin/python tensorflow_serving/model_servers:tensorflow_model_server
```
You can then copy bazel-bin/tensorflow_serving/model_servers/tensorflow_model_server elsewhere and run it with appropriate `LD_LIBRARY_PATH`. To clean the build artifacts `bazelisk clean --expunge`.

There are some test models provided, to test: (based on https://github.com/tensorflow/serving/blob/master/tensorflow_serving/g3doc/docker.md#tensorflow-serving-with-docker)
```
tensorflow_model_server --model_base_path=/home/okosarko/tensorflow-serving/tensorflow_serving/servables/tensorflow/testdata/saved_model_half_plus_two_gpu/ --model_name=half_plus_two --rest_api_port=8501
```
```
curl -d '{"instances": [1.0, 2.0, 5.0]}' http://localhost:8501/v1/models/half_plus_two:predict
```
Few steps back you can also test cudnn (samples are in deb package downloadable separtely from src, use dpkg -x to unpack) and TensorRT

## Configs
There are several config files:
- for serving
  - [model.config](./model.config) - with model names and path; names can be arbitrary (usually src-tgt)
  - [batching.config](./batching.config) - batch configuration
- for systemd
  - see [systemd](./systemd) - service definitions for systemd (might need tweaking if using multiple systems)
  - to check how tensorflow is started see [tensorflow_serving.service](./systemd/tensorflow_serving.service)
  - The systemd template file for marian uses the `src-tgt` model name to reference various files and directories. E.g. `cp systemd/marian@.service /etc/systemd/system; systemctl enable marian@cs-de.service; systemctl start marian@cs-de.service` should use env file `marian_cs-de.conf` and set a working directory `marian-models/cs-de`
- application config
  - [app/settings.py](app/settings.py)
    - keep `BATCH_SIZE` in sync with `batching.config`
    - `SENT_LEN_LIMIT` limits the max length of sent in chars
  - [app/models.json](app/models.json) - a list defining model2problem, model2server, source & target mappings etc
```
  {
    "model_framework": "tensorflow", // optional, tensorflow is default, the other values are tensorflow_doclevel and marian
    "source": ["en"], // a list of src languages supported by the model, usually len==1
    "target": ["cs", "de", "es", "fr", "hu", "pl", "sv"], // a list of tgt languages, usually len==1
    "problem": "translate_medical8lang", // t2t problem
    "domain": "medical", // shown in display if display omitted
    "model": "cs-es_medical", // servable name in model.config
    "display": "Experimentální překlad", // optional, override the default display name
    "prefix_with": "SRC{source} TRG{target} ", // optional, this is added before each sentence
    "target_to_source": true, // optional, this model supports translation from target to source (eg. also cs->en)
    "include_in_graph": false, // optional, don't include this model in the shortest path search, ie. make it available only in advanced mode
    "server": "{T2T_TRANSFORMER2}", // ip/hostname + port, interpolated with app config
    "default": false,
    "batch_size": 7 // optional, override {MARIAN_}BATCH_SIZE from settings.py for this model
    //other options for marian
  }
```
    
  
## Adding new model
Assume we have two machines `flask` and `gpu`
0. see `scripts/export.sh` or https://github.com/tensorflow/tensor2tensor/blob/ae042f66e013494eb2c4c2b50963da5a3d3fc828/tensor2tensor/serving/README.md#1-export-for-serving , but set the appropriate params. Pick a name (`$MODEL`)
1. update `app/models.json` appropriately, `model` is `$MODEL` (this needs to be on `flask`)
2. add dictionary to [t2t_data_dir](t2t_data_dir) (this needs to be on `flask`)
3. update `model.config`, `name` is `$MODEL` (this lives on `gpu`, the systemd scripts expects that file in `/opt/lindat_tranformer_service`)
4. restart both - `sudo systemctl restart tensorflow_serving`, `sudo systemctl restart transformer`
5. check serving logs for oom errors `sudo journalctl -f -u tensorflow_serving`; if you see them before translating anything, search for a way to dynamically swap the models; if you see them when translating you might try fiddling with `batching.config`
