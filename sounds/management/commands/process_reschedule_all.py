from django.core.management.base import NoArgsCommand
from sounds.models import Sound
from django.db.models import Q

class Command(NoArgsCommand):
    args = '<num_days>'
    help = 'Take all sounds that are sitting the processing queue marked as "queue" and reschedule them'

    def handle(self, **options):
        Sound.objects.filter(Q(processing_state='PR') | Q(processing_state='QU')).update(processing_state = "PE")
