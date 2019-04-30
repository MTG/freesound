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

from __future__ import print_function

import errno
import hashlib
import os
import shutil
import sys
import warnings
import zlib
from tempfile import mkdtemp


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
    fh = open(filename, "rb")
    digest = hashlib.md5()
    with open(filename, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            digest.update(chunk)
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


def remove_directory_if_empty(path):
    if not os.listdir(path):
        os.rmdir(path)


def create_directories(path, exist_ok=True):
    """
    Creates directory at the specified path, including all intermediate-level directories needed to contain it.
    NOTE: after migrating to Python3, this util function can be entirely replaced by calling
    "os.makedirs(path, exist_ok=True)".
    :param str path: path of the direcotry to create
    :param bool exist_ok: if set to True, exceptions won't be raised if the target direcotry already exists
    """
    try:
        os.makedirs(path)
    except OSError as exc:
        # Ignore exception if directory already existing
        if exist_ok and exc.errno != errno.EEXIST:
            raise


def remove_directory(path):
    """
    Removes the directory at the specified path and all of its contents (including files and other direcotries).
    No exception is raised if no direcotry exists at the given path.
    :param str path: path of the direcotry to delete
    """
    try:
        shutil.rmtree(path)
    except OSError as e:
        # Ignore exception if directory does not exist
        if e.errno != errno.ENOENT:
            raise


class TemporaryDirectory(object):

    """Create and return a temporary directory.  This has the same
    behavior as mkdtemp but can be used as a context manager.  For
    example:

        with TemporaryDirectory() as tmpdir:
            ...

    Upon exiting the context, the directory and everything contained
    in it are removed.

    This is a backport of tempfile.TemporaryDirectory() which is only available in Python 3.2+. Code has been coppied
    from this post: https://stackoverflow.com/questions/19296146/tempfile-temporarydirectory-context-manager-in-python-2-7
    Once migrating to Python 3, we can remove this code and use the default implementation in tempfile package.
    """

    def __init__(self, suffix="", prefix="tmp", dir=None):
        self._closed = False
        self.name = None  # Handle mkdtemp raising an exception
        self.name = mkdtemp(suffix, prefix, dir)

    def __repr__(self):
        return "<{} {!r}>".format(self.__class__.__name__, self.name)

    def __enter__(self):
        return self.name

    def cleanup(self, _warn=False):
        if self.name and not self._closed:
            try:
                self._rmtree(self.name)
            except (TypeError, AttributeError) as ex:
                # Issue #10188: Emit a warning on stderr
                # if the directory could not be cleaned
                # up due to missing globals
                if "None" not in str(ex):
                    raise
                print("ERROR: {!r} while cleaning up {!r}".format(ex, self, ),
                      file=sys.stderr)
                return
            self._closed = True
            if _warn:
                self._warn("Implicitly cleaning up {!r}".format(self),
                           ResourceWarning)

    def __exit__(self, exc, value, tb):
        self.cleanup()

    def __del__(self):
        # Issue a ResourceWarning if implicit cleanup needed
        self.cleanup(_warn=True)

    # XXX (ncoghlan): The following code attempts to make
    # this class tolerant of the module nulling out process
    # that happens during CPython interpreter shutdown
    # Alas, it doesn't actually manage it. See issue #10188
    _listdir = staticmethod(os.listdir)
    _path_join = staticmethod(os.path.join)
    _isdir = staticmethod(os.path.isdir)
    _islink = staticmethod(os.path.islink)
    _remove = staticmethod(os.remove)
    _rmdir = staticmethod(os.rmdir)
    _warn = warnings.warn

    def _rmtree(self, path):
        # Essentially a stripped down version of shutil.rmtree.  We can't
        # use globals because they may be None'ed out at shutdown.
        for name in self._listdir(path):
            fullname = self._path_join(path, name)
            try:
                isdir = self._isdir(fullname) and not self._islink(fullname)
            except OSError:
                isdir = False
            if isdir:
                self._rmtree(fullname)
            else:
                try:
                    self._remove(fullname)
                except OSError:
                    pass
        try:
            self._rmdir(path)
        except OSError:
            pass
