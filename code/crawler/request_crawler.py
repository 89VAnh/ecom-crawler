import requests
import traceback 
from sink.sink import Sink
import json
import time
from util import data_util
import copy
from error.page_end_error import PageEndError
from transform.transform import Transform

class RequestCrawler():
    def __init__(self, pipeline):
        self.pipeline = pipeline

    def get(self, input_val ,**kwargs):
        try:
            params = data_util.format_params(kwargs.get("params"), kwargs)
            response = requests.get(
                kwargs.get("url"), 
                params=params, 
                headers=kwargs.get("headers"), 
                data=kwargs.get("data"), 
                cookies=kwargs.get("cookies")
            )
            if kwargs.get("format"):
                result = response.__getattribute__(kwargs.get("format"))()
            else:
                result = response.raw
            if kwargs.get("cond"):
                expr = kwargs["cond"]["validate"]
                if eval(expr):
                    raise PageEndError(f"done")
            return result
        except PageEndError as e:
            raise e
        except Exception as e:
            traceback.print_exc()
    
    def save(self, input_val, **kwargs):
        result = Sink(kwargs.get("type"), input_val, **kwargs).execute()
        return result
    
    def clear_sink(self, input_val, **kwargs):
        Sink(kwargs.get("type"), input_val, **kwargs).clear()
    
    def transform(self, input_val, **kwargs):
        return Transform(input_val, **kwargs).process()

    def foreach(self, input_val, **kwargs):
        iterator = []
        if isinstance(input_val, list):
            iterator = input_val
        if kwargs.get("limit"):
            limit = kwargs.get("limit")
            start = 0
            step = 1
            if kwargs.get("start"):
                start  = kwargs.get("start")
            if kwargs.get("step"):
                step = kwargs.get("step")
            iterator = range(start, limit, step)
            
        for item in iterator:
            actions = copy.deepcopy(kwargs["actions"])
            tmp_val = item
            for action in actions:
                try:
                    params = action["params"]
                    params["item"] = item
                    if kwargs.get("cond"):
                        if kwargs["cond"]["action"] == action.get("name"):
                            params["cond"] = kwargs["cond"]
                    tmp_val = getattr(self,action.get("name"))(tmp_val, **params)
                except PageEndError as e:
                    raise e
                except Exception as e:
                    traceback.print_exc()
            if kwargs.get("delay"):
                time.sleep(kwargs.get("delay"))
        return tmp_val
    
    def run(self):
        tmp_val = None
        for action in self.pipeline:
            method = getattr(self, action.get("name"))
            tmp_val = method(tmp_val, **action.get("params"))
        return tmp_val
    

