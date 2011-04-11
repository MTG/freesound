import md5
import os
import zlib

class File:
    
    def __init__(self, id, name, full_path, is_dir):
        self.name = name
        self.full_path = full_path
        self.is_dir = is_dir
        self.children = [] if is_dir else None
        self.id = "file%d" % id
    
    def recursive_print(self, spacer=""):
        print spacer + self.name
        if self.is_dir:
            for child in self.children:
                child.recursive_print(spacer + "  ")    

def generate_tree(path):
    counter = 0
    lookups = {path: File(counter, path, path, True)}
    files = {}
    
    for (root, dirnames, filenames) in os.walk(path):
        parent = lookups[root]
    
        for dirname in sorted(dirnames):
            full_path = os.path.join(root, dirname)
            file_object = File(counter, dirname, full_path, True)
            counter += 1
            lookups[full_path] = file_object
            parent.children.append(file_object)
            
        for filename in sorted(filenames):
            full_path = os.path.join(root, filename)
            file_object = File(counter, filename, full_path, False)
            counter += 1
            files[file_object.id] = filename
            parent.children.append(file_object)
            

    return lookups[path], files

def md5file(filename):
    """Return the hex digest of a file without loading it all into memory"""
    fh = open(filename, "rb")
    digest = md5.new()
    while 1:
        buf = fh.read(4096)
        if buf == "":
            break
        digest.update(buf)
    fh.close()
    return digest.hexdigest()

def crc32file(filename):
    fh = open(filename, "rb")
    crc32 = 0
    while 1:
        buf = fh.read(4096)
        if buf == "":
            break
        crc32 = zlib.crc32(buf, crc32)
    fh.close()
    return hex(crc32)[2:]