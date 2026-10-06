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

import pytest

from general.templatetags.util import samplerate_with_units, smart_duration_with_units


def test_smart_duration_with_units():
    assert smart_duration_with_units(100) == "1:40 minutes"
    assert smart_duration_with_units(3620) == "1:00 hours"
    assert smart_duration_with_units(3694) == "1:01 hours"


@pytest.mark.parametrize(
    "rate,expected",
    [
        (96000.0, "96 kHz"),
        (44100.0, "44.1 kHz"),
        (11025.0, "11.025 kHz"),
        (192000, "192 kHz"),
        (30223.0, "30.223 kHz"),
        (30223.123456789, "30.223 kHz"),
        (30223.6, "30.224 kHz"),
        (44099.999, "44.1 kHz"),
        (7119, "7.119 kHz"),
        (48048, "48.048 kHz"),
        (0, "0 Hz"),
    ],
)
def test_samplerate_with_units(rate, expected):
    assert samplerate_with_units(rate) == expected
