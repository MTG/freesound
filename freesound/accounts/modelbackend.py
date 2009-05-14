from django.contrib.auth.models import User
from django.contrib.auth.backends import ModelBackend

class CustomModelBackend(ModelBackend):
    def authenticate(self, username=None, password=None):
        """ authenticate against case insensitive username """
        try:
            user = User.objects.get(username__iexact=username)
            if user.check_password(password):
                return user
        except User.DoesNotExist:
            return None