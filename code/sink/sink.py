from sink.file_sink import FileSink
from sink.jdbc_sink import JDBCSink
from sink.s3_sink import S3Sink
from sink.memory_sink import MemorySinhk

class Sink():
    def __new__(cls, sink_type, data, **kwargs):
        match sink_type:
            case 'file':
                return FileSink(data, **kwargs)
            case 's3':
                return S3Sink(data, **kwargs)
            case 'jdbc':
                return JDBCSink(data, **kwargs)
            case 'memory':
                return MemorySinhk(data, **kwargs)
            case _:
                return super().__new__(cls)
    
    def execute(self):
        raise NotImplementedError()
    
    def clear(self):
        raise NotImplementedError()
    
