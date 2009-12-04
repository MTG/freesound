from Crypto.Cipher import AES
from django.conf import settings
import base64
import urllib

def encrypt(decrypted_string):
    encryptor = AES.new(settings.SECRET_KEY[0:16])
    
    # encrypted strings need to be len() = multiple of 16
    decrypted_string += u' ' * ( 16 - len(decrypted_string) % 16 )

    encrypted_string = encryptor.encrypt(decrypted_string)
    
    # base64 encoded strings have "=" signs, quote them!
    encoded_string = urllib.quote(base64.b64encode(encrypted_string))
    
    return encoded_string

def decrypt(quoted_string):
    decryptor = AES.new(settings.SECRET_KEY[0:16])
    
    encoded_string = urllib.unquote(quoted_string)
    
    encrypted_string = base64.b64decode(encoded_string)
    
    decrypted_string = decryptor.decrypt(encrypted_string).strip()
    
    return decrypted_string 