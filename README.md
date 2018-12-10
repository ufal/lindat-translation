# transformer_frontend
A simple flask based ui in front of tensorflow serving.

In our setup the flask app runs on a machine called `transformer` and tensorflow serving on another machine called `t2t-transformer`.

## Install

*TBD*

## Configs
There are several config files:
- for serving
  - [model.config](./model.config) - with model names and path; names are src-tgt_model
  - [batching.config](./batching.config) - batch configuration
- for systemd
  - see [systemd](./systemd) - service definitions for systemd (might need tweaking if using multiple systems)
  - to check how tensorflow is started see [tensorflow_serving.service](./systemd/tensorflow_serving.service)
- application config
  - [app/settings.py](app/settings.py)
    - keep `BATCH_SIZE` in sync with `batching.config`
    - `SENT_LEN_LIMIT` limits the max length of sent in chars
  - [app/main/views.py](app/main/views.py) - *these will probably move into `settings.py` in the future*
    - `_choices` - src-tgt (without _model) to human readable mapping
    - `model2problem` - src-tgt (without _model) to t2t problem instance mapping
    - `request_fn` - contains server details
  
## Adding new model
0. get Dusan to convert model to the right format (and put the data on `t2t-transformer`)
1. update `_choices`, `model2problem` accordingly (on `transformer`)
2. Upload dictionary to [t2t_data_dir](t2t_data_dir) (on `transformer`)
3. update `model.config` with the new model (on `t2t-transformer` the systemd scripts expects that file in `/opt/lindat_tranformer_service`)
4. restart both - `sudo systemctl restart tensorflow_serving`, `sudo systemctl restart transformer`
5. check serving logs for oom errors `sudo journalctl -f -u tensorflow_serving`; if you see them before translating anything, search for a way to dynamically swap the models; if you see them when translating you might try fiddling with `batching.config`


## Notes
The first version (where the translation was run as a shell script) was based on https://beenje.github.io/blog/posts/running-background-tasks-with-flask-and-rq/ - the look and forms are still based on that
