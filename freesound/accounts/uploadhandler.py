from django.core.files.uploadhandler import FileUploadHandler
from django.core.cache import cache

class ProgressUploadHandler(FileUploadHandler):
    def __init__(self, unique_id):
        super(FileUploadHandler, self).__init__()
        self.unique_id = unique_id
        self.data_received = 0
    
    # rewrite to write json!
    def receive_data_chunk(self, raw_data, start):
        self.data_received += len(raw_data)

        cache.set(self.unique_id, {"received": self.data_received, "total": self.content_length}, 60)

        return raw_data
    
    def file_complete(self, file_size):
        cache.set(self.unique_id, {"received": file_size, "total": file_size}, 60)
        
        return None