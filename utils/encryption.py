from django.conf import settings

def encrypt(decrypted_string):
    from Crypto.Cipher import AES
    import base64
    import urllib
    
    encryptor = AES.new(settings.SECRET_KEY[0:16]) #@UndefinedVariable
    
    # encrypted strings need to be len() = multiple of 16
    decrypted_string += u' ' * ( 16 - len(decrypted_string) % 16 )

    encrypted_string = encryptor.encrypt(decrypted_string)
    
    # base64 encoded strings have "=" signs, quote them!
    encoded_string = urllib.quote(base64.b64encode(encrypted_string).replace("/", ".").replace("+", "_").replace("=", "-"))
    
    return encoded_string

def decrypt(quoted_string):
    from Crypto.Cipher import AES
    import base64
    import urllib

    decryptor = AES.new(settings.SECRET_KEY[0:16]) #@UndefinedVariable
    
    encoded_string = urllib.unquote(quoted_string)
    
    encrypted_string = base64.b64decode(encoded_string.replace(".", "/").replace("_", "+").replace("-", "="))
    
    decrypted_string = decryptor.decrypt(encrypted_string).strip()
    
    return decrypted_string 

def create_hash(data):
    import hashlib
    m = hashlib.md5()
    m.update(str(data) + settings.SECRET_KEY)
    return m.hexdigest()[0:8]