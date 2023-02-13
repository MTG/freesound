#
# Freesound is (c) MUSIC TECHNOLOGY GROUP, UNIVERSITAT POMPEU FABRA
#
# Freesound is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# Freesound is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# Authors:
#     See AUTHORS file.
#


import hashlib
import os
import shutil
import zlib


class File:

    def __init__(self, id, name, full_path, is_dir):
        self.name = name
        self.full_path = full_path
        self.is_dir = is_dir
        self.children = [] if is_dir else None
        self.id = "file%d" % id

    def recursive_print(self, spacer=""):
        print(spacer + self.name)
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
            files[file_object.id] = file_object
            parent.children.append(file_object)

    return lookups[path], files


def md5file(filename):
    """Return the hex digest of a file without loading it all into memory"""
    digest = hashlib.md5()
    with open(filename, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            digest.update(chunk)
    return digest.hexdigest()


def crc32file(filename):
    fh = open(filename, "rb")
    crc32 = 0
    while True:
        buf = fh.read(4096)
        if buf == "":
            break
        crc32 = zlib.crc32(buf, crc32)
    fh.close()
    return hex(crc32)[2:]


def remove_directory(path):
    shutil.rmtree(path)


def remove_directory_if_empty(path):
    if not os.listdir(path):
        try:
            os.rmdir(path)
        except OSError:
            # Directory not really empty (could happen if a file was just created)
            pass
