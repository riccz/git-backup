import logging
import logging.config
from pathlib import Path
from typing import Optional

import pkg_resources
import yaml


logger = logging.getLogger(__name__)


def merge_dicts(base: dict, update: dict):
    for k, v in update.items():
        if k in base and isinstance(v, dict):
            merge_dicts(base[k], v)
        else:
            base[k] = v


def get_deep(container, *keys, default=None):
    for k in keys:
        if k not in container:
            return default
        else:
            container = container[k]
    return container


def set_deep(container, *keys, value):
    assert len(keys) > 0, "Cannot set with no keys"
    for k in keys[:-1]:
        if k not in container:
            container[k] = {}  # FIXME: What if the next key is `int`?
        container = container[k]
    container[keys[-1]] = value


def read_default_config():
    raw_yaml = pkg_resources.resource_string(__name__,
                                             'data/default_config.yml')
    return yaml.safe_load(raw_yaml)


def load_config(config_path: str):
    config_exp_path = Path(config_path).expanduser()
    with config_exp_path.open('r') as c:
        config = yaml.safe_load(c.read())
    merged_config = read_default_config()
    merge_dicts(merged_config, config)
    return merged_config


def setup_logging(config: dict, verbose: int = 0):
    logging.config.dictConfig(config['logging'])

    assert verbose >= 0
    if verbose > 0:
        top_logger = logging.getLogger('git_backup')
        current_level = top_logger.getEffectiveLevel()
        top_logger.setLevel(max(current_level - 10 * verbose, logging.DEBUG))
