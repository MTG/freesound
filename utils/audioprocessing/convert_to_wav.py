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

from .processing import AudioProcessingException, audio_info, convert_to_wav

convert_to_wav(sys.argv[1], sys.argv[2])

try:
    info = audio_info(sys.argv[2])
    if not (info["bits"] == 16 and info["samplerate"] == 44100 and info["channels"] == 2 and info["duration"] > 0):
        print("warning, created file is not 44.1, stereo, 16bit!")
except AudioProcessingException as e:
    print("warning, audio processing seems to have failed:", e)
