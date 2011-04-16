import os

from django.db.models.signals import post_syncdb
from django.dispatch import receiver
from settings import SOUNDS_PATH, PACKS_PATH, UPLOADS_PATH
from settings import AVATARS_PATH, PREVIEWS_PATH, DISPLAYS_PATH

@receiver(post_syncdb)
def create_locations(sender, **kwargs):
    for folder in [SOUNDS_PATH, PACKS_PATH, AVATARS_PATH, UPLOADS_PATH,
        PREVIEWS_PATH, DISPLAYS_PATH]:
            if not os.path.isdir(folder):
                try:
                    os.mkdir(folder)
                    print ("Successfullly created the folder: '%s'" % folder)
                except Exception, e:
                    print ("Problem creating this folder: '%s', %s"
                        % (folder, e))
            else:
                print ("Folder: '%s' already exists" % folder)


