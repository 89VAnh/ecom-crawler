import json
import boto3
from util import data_util


class S3Sink:
    def __init__(self, data, **kwargs):
        self.data = data
        self.kwargs = kwargs

    def execute(self):
        bucket = self.kwargs.get("bucket")
        file_key = self.kwargs.get("key")

        pattern_dict = self.kwargs.get("pattern", {})
        for key, val in pattern_dict.items():
            formatted_val = data_util.format_pattern(val)
            file_key = file_key.replace(key, formatted_val)

        ndjson_data = "\n".join([json.dumps(item) for item in self.data])

        client = boto3.client("s3")
        client.put_object(Bucket=bucket, Key=file_key, Body=ndjson_data)
