from django.conf import settings
from django.core.cache import cache
from django.core.files.uploadhandler import FileUploadHandler
import datetime

class ProgressUploadHandler(FileUploadHandler):
    def __init__(self, unique_id):
        super(FileUploadHandler, self).__init__()
        self.unique_id = unique_id
        self.data_received = 0
        self.start = datetime.datetime.now()
        self.seconds_elapsed = 0
    
    def receive_data_chunk(self, raw_data, start):
        self.data_received += len(raw_data)
        
        now = datetime.datetime.now()
        seconds_elapsed = (now - self.start).seconds
        # update the cache once every second
        if seconds_elapsed != self.seconds_elapsed:
            self.seconds_elapsed = seconds_elapsed
            cache.set(self.unique_id, {"unique_id": self.unique_id, "file_name": self.file_name, "received": self.data_received, "total": self.content_length}, 60)

        return raw_data
    
    def file_complete(self, file_size):
        cache.set(self.unique_id, {"unique_id": self.unique_id, "file_name": self.file_name, "received": file_size, "total": file_size}, 60)
        
        return None