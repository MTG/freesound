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

def encrypt(decrypted_string):
    from Crypto.Cipher import AES
    import base64
    import urllib.request, urllib.parse, urllib.error
    
    encryptor = AES.new(settings.SECRET_KEY[0:16]) #@UndefinedVariable
    
    # encrypted strings need to be len() = multiple of 16
    decrypted_string += u' ' * ( 16 - len(decrypted_string) % 16 )

    encrypted_string = encryptor.encrypt(decrypted_string)
    
    # base64 encoded strings have "=" signs, quote them!
    encoded_string = urllib.parse.quote(base64.b64encode(encrypted_string).replace("/", ".").replace("+", "_").replace("=", "-"))
    
    return encoded_string

def decrypt(quoted_string):
    from Crypto.Cipher import AES
    import base64
    import urllib.request, urllib.parse, urllib.error

    decryptor = AES.new(settings.SECRET_KEY[0:16]) #@UndefinedVariable
    
    encoded_string = urllib.parse.unquote(quoted_string)
    
    encrypted_string = base64.b64decode(encoded_string.replace(".", "/").replace("_", "+").replace("-", "="))
    
    decrypted_string = decryptor.decrypt(encrypted_string).strip()
    
    return decrypted_string 

def create_hash(data, add_secret=True, limit=8):
    import hashlib
    m = hashlib.md5()
    if add_secret:
        m.update(str(data) + settings.SECRET_KEY)
    else:
        m.update(str(data))
    return m.hexdigest()[0:limit]