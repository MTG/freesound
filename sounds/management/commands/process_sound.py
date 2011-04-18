from django.core.management.base import BaseCommand, CommandError
from utils.audioprocessing.freesound_audio_processing import process_sound_via_gearman
from sounds.models import Sound

class Command(BaseCommand):
    args = '<sound_id sound_id ...>'
    help = 'Post a sound to the gearman process sound queue'

    def handle(self, *args, **options):
        for sound_id in args:
            try:
                sound = Sound.objects.get(pk=int(sound_id))
            except Sound.DoesNotExist:
                raise CommandError('Sound "%s" does not exist' % sound_id)
            self.stdout.write('Posting sound to gearman "%s"\n' % sound.id)
            process_sound_via_gearman(sound)