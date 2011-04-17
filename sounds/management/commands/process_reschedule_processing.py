from django.core.management.base import NoArgsCommand
from sounds.models import Sound

class Command(NoArgsCommand):
    args = '<num_days>'
    help = 'Take all sounds that are sitting the processing queue marked as "being processed" and reschedule them'

    def handle(self, **options):
        for sound in Sound.objects.filter(processing_state="PR"):
            sound.processing_state = "PE"
            sound.save()