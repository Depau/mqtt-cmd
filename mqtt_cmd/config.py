# noinspection PyShadowingNames
import yaml


def read_config(path: str) -> dict:
    with open(path) as f:
        cfg = yaml.load(f, Loader=yaml.SafeLoader)
        return cfg
