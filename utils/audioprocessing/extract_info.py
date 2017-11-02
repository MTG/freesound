#!/usr/bin/env python

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

import sys
from processing import stereofy_and_find_info, AudioProcessingException

try:
    for (k,v) in stereofy_and_find_info("/Users/bram/Development/nightingale/sandbox/legacy/stereofy/stereofy", sys.argv[1], '/dev/null').items():
        print k,"->", v
except AudioProcessingException as e:
    print "warning, audio information extraction seems to have failed:", e
