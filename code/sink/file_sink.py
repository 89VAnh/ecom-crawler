import json
from util import data_util

import os


class FileSink:
    def __init__(self, data, **kwargs):
        self.kwargs = kwargs
        self.data = data

    def execute(self):
        file_name = self.kwargs.get("file_name")
        write_mode = self.kwargs.get("write_mode", "w")

        pattern_dict = self.kwargs.get("pattern", {})
        for key, val in pattern_dict.items():
            formatted_val = data_util.format_pattern(val)
            file_name = file_name.replace(key, formatted_val)

        directory = os.path.dirname(file_name)
        if directory:
            os.makedirs(directory, exist_ok=True)

        self.data = data_util.convert_data(self.data)

        with open(file_name, mode=write_mode) as f:
            for item in self.data:
                json.dump(item, f, ensure_ascii=False)
                f.write("\n")
