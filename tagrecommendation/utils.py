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

import json
from numpy import zeros
import sys


def loadFromJson(path, verbose=False):
    with open(path, 'r') as f:
        if verbose:
            print("Loading data from '" + path + "'")
        return json.load(f)


def saveToJson(path="", data="", verbose=True):
    with open(path, mode='w') as f:
        if verbose:
            print("Saving data to '" + path + "'")
        json.dump(data, f, indent=4)


def mtx2npy(M, verbose=True):
    n = M.shape[0]
    m = M.shape[1]
    npy = zeros((n, m), 'float32')
    #non_zero_index = M.keys()
    items = list(M.items())
    nItems = len(M.items())
    done = 0
    #for index in non_zero_index :
    for index, value in items:
        npy[index[0]][index[1]] = value    #M[ index[0] , index[1] ]

        done += 1
        if verbose:
            sys.stdout.write("\rConverting to npy... " + '%.2f' % ((float(done) * 100) / float(nItems)) + "% ")
            sys.stdout.flush()

    if verbose:
        sys.stdout.write("\n")
        sys.stdout.flush()
    return npy
