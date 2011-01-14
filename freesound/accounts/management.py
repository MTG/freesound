from accounts import models as auth_models
from django.db.models.signals import post_syncdb
from django.contrib.auth.models import User
from accounts.models import Profile


def create_super_profile(**kwargs):
    print '== create profile for super user =='
    userA = User.objects.filter(is_superuser=True)[0]
    profile = Profile(user=userA)
    profile.save()

post_syncdb.connect(create_super_profile, sender=auth_models)

