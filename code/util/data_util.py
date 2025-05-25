from datetime import datetime, timezone
import json


def format_params(params, value_dict):
    for param in params.keys():
        if isinstance(params.get(param), str):
            if params.get(param).startswith("$"):
                value_key = params[param].replace("$", "")
                params[param] = value_dict.get(value_key)
    return params


def get_time_now(time_format):
    now = datetime.now().replace(tzinfo=timezone.utc)
    return now.strftime(time_format)


def execute_get_time(func_name):
    t_format = func_name.split("@")[-1]
    return get_time_now(t_format)


def format_pattern(pattern):
    if pattern.startswith("#"):
        return execute_get_time(pattern.replace("#", ""))
    return pattern


def convert_data(data):
    if isinstance(data, dict) or isinstance(data, list):
        return json.dumps(data, ensure_ascii=False).encode("utf-8")
    return data
