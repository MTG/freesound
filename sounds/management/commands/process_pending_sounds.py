from django.core.management.base import NoArgsCommand
from utils.audioprocessing.freesound_audio_processing import process_sound_via_gearman
from sounds.models import Sound
import gearman
from django.conf import settings

class Command(NoArgsCommand):
    help = 'Process all the sounds'

    def handle(self, **options):
        gm_client = gearman.GearmanClient(settings.GEARMAN_JOB_SERVERS)
        for sound in Sound.objects.filter(processing_state="PE").exclude(original_path=None):
            self.stdout.write('Posting sound to gearman "%s"\n' % sound.id)
            process_sound_via_gearman(sound, gm_client)