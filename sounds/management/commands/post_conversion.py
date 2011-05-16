from django.core.management.base import NoArgsCommand
from sounds.models import Sound
import os

class Command(NoArgsCommand):
    help = "Determine which sounds have already been copied from FS1 and processed and set processing_state accordingly."

    def handle(self, **options):
        sounds = Sound.objects.filter(processing_state='PE')
        counter = 0
        for sound in sounds:
            # check some random paths
            if os.path.exists(sound.locations('path')) and \
               os.path.exists(sound.locations('preview.HQ.mp3.path')) and \
               os.path.exists(sound.locations('analysis.statistics.path')) and \
               os.path.exists(sound.locations('display.spectral.L.path')):
                sound.processing_state = 'OK'
                sound.save()
            counter += 1
            if counter % 1000 == 0:
                print 'Processed %s sounds' % counter

