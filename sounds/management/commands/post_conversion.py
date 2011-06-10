from django.core.management.base import NoArgsCommand
from sounds.models import Sound, Pack
from django.db.models import Q
from django.contrib.auth.models import User
from similarity.client import Similarity
import os


#BAD_USERNAME_CHARACTERS = ' '

class Command(NoArgsCommand):
    help = """ 1) Determine which sounds have already been copied from FS1 and processed and set processing_state accordingly.
               2) Update the num_comments field on sound
           """

    def handle(self, **options):

        # Update sounds
        sounds = Sound.objects.all()
        counter = 0
        for sound in sounds:

            # check some random paths
            if sound.processing_state != 'OK' and \
               os.path.exists(sound.locations('path')) and \
               os.path.exists(sound.locations('preview.HQ.mp3.path')) and \
               os.path.exists(sound.locations('display.spectral.L.path')):
                sound.processing_state = 'OK'

            if sound.analysis_state != 'OK' and \
               os.path.exists(sound.locations('analysis.statistics.path')) and \
               os.path.exists(sound.locations('analysis.frames.path')):
                sound.analysis_state = 'OK'

            if sound.analysis_state == 'OK' and \
               Similarity.contains(sound.id):
                sound.similarity_state = 'OK'

            sound.save()

            counter += 1
            if counter % 1000 == 0:
                print 'Processed %s sounds' % counter


#        print '-- replace bad username characters --'
#        # construct filter
#        query_components = []
#        for bad_char in BAD_USERNAME_CHARACTERS:
#            query_components.append(Q(username__contains=bad_char))
#        query_filter = reduce(lambda x, y: x|y, query_components)
#        # replace characters
#        query = User.objects.filter(query_filter).filter(num_sounds>=0)
#        user_count = query.count()
#        new_names = {}
#        for user in query:
#            changed, fs2_username = transform_username_fs1fs2(user.username)
#            # remember new name and count
#            if fs2_username in new_names:
#                new_names[fs2_username] = new_names[fs2_username]+1
#            else:
#                new_names[fs2_username] = 1
#
#        for username in new_names.keys():
#            if new_names[username] > 1:
#                print username, new_names[username]
#
#        print user_count


