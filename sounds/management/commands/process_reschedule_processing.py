from django.core.management.base import BaseCommand
from sounds.models import Sound
from datetime import datetime

class Command(BaseCommand):
    args = '<num_days>'
    help = 'Take all sounds that have been sitting the processing queue marked as "being processed" and reschedule them'

    def handle(self, *args, **options):
        num_days = int(args[0])
        for sound in Sound.objects.filter(processing_state="PR", processing_date__lt=datetime.now()-datetime.timedelta(num_days)):
            sound.processing_state = "PE"
            sound.save()