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

import os


def create_test_files(filenames, directory, n_bytes=1024):
    """
    This function generates test files ith random content and saves them in the specified directory.
    :param filenames: list of names for the files to generate
    :param directory: folder where to store the files
    :param n_bytes: numnber of bytes of each generated file
    """
    for filename in filenames:
        f = open(os.path.join(directory, filename), 'a')
        f.write(os.urandom(n_bytes))
        f.close()
