import os
import yaml

_cache = {}


def load_yaml(path: str):
    if not path or not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def get_base_conf():
    if "base" not in _cache:
        _cache["base"] = load_yaml("config/base.yaml")
    return _cache["base"]


def get_task_conf():
    if "task" not in _cache:
        _cache["task"] = load_yaml("config/task.yaml")
    return _cache["task"]

