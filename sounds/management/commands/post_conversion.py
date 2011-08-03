from django.core.management.base import NoArgsCommand
from sounds.models import Sound
from django.contrib.auth.models import User
from similarity.client import Similarity
from django.db.models import Max
import os


#BAD_USERNAME_CHARACTERS = ' '

class Command(NoArgsCommand):
    help = """ 1) Determine which sounds have already been copied from FS1 and processed and set processing_state accordingly.
               2) Update the num_comments field on sound
           """

    def handle(self, **options):

        # Update sounds
        max_sound_id = Sound.objects.all().aggregate(Max('id'))['id__max']
        counter = 0

        for sound_id in xrange(max_sound_id+1):

            changed = False
            try:
                sound = Sound.objects.get(id=sound_id)
            except Sound.DoesNotExist:
                continue

            # check some random paths
            if sound.processing_state != 'OK' and \
               os.path.exists(sound.locations('path')) and \
               os.path.exists(sound.locations('preview.HQ.mp3.path')) and \
               os.path.exists(sound.locations('display.spectral.L.path')):
                sound.processing_state = 'OK'
                changed = True


            if sound.analysis_state != 'OK' and \
               os.path.exists(sound.locations('analysis.statistics.path')) and \
               os.path.exists(sound.locations('analysis.frames.path')):
                sound.analysis_state = 'OK'
                changed = True

            if sound.analysis_state == 'OK' and Similarity.contains(sound.id):
                sound.similarity_state = 'OK'
                changed = True

            if changed:
                sound.save()

            counter += 1
            if counter % 1000 == 0:
                print 'Processed %s sounds' % counter
