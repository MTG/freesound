from django.contrib.auth.models import User
from django.db import models
from django.utils.encoding import smart_unicode
import uuid

def generate_key():
    return ''.join(str(uuid.uuid4()).split('-'))

class ApiKey(models.Model):
    key            = models.CharField(max_length=32, default=generate_key)
    user           = models.ForeignKey(User, related_name='api_keys')
    valid          = models.BooleanField(default=True)
    description    = models.TextField(blank=True)
