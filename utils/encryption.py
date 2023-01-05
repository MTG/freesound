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

from future import standard_library
standard_library.install_aliases()
from builtins import str
from django.conf import settings

from django.core.signing import TimestampSigner


def sign_with_timestamp(unsigned_value):
    signer = TimestampSigner()
    value = signer.sign(unsigned_value)
    orig_val, signed_value = value.split(":", maxsplit=1)
    return signed_value


def unsign_with_timestamp(unsigned_value, signed_value, max_age):
    signer = TimestampSigner()
    value = signer.unsign(":".join((unsigned_value, signed_value)), max_age)
    return value


def create_hash(data, add_secret=True, limit=8):
    import hashlib
    m = hashlib.md5()
    if add_secret:
        m.update(str(data) + settings.SECRET_KEY)
    else:
        m.update(str(data))
    return m.hexdigest()[0:limit]
