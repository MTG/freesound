import os

from django.db.models.signals import post_syncdb
from django.dispatch import receiver
from django.conf import settings

@receiver(post_syncdb)
def create_locations(sender, **kwargs):
    for folder in [settings.SOUNDS_PATH, settings.PACKS_PATH, settings.AVATARS_PATH, settings.UPLOADS_PATH,
                   settings.PREVIEWS_PATH, settings.DISPLAYS_PATH]:
            if not os.path.isdir(folder):
                try:
                    os.mkdir(folder)
                    print ("Successfullly created the folder: '%s'" % folder)
                except Exception, e:
                    print ("Problem creating this folder: '%s', %s"
                        % (folder, e))
            else:
                print ("Folder: '%s' already exists" % folder)
