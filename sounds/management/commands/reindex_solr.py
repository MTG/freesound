from django.core.management.base import BaseCommand
from django_extensions.management.jobs import DailyJob
from sounds.models import Sound
from utils.search.search import add_all_sounds_to_solr

class Command(BaseCommand):
    args = ''
    help = 'Take all sounds and send them to Solr'

    def handle(self, *args, **options):
        sound_qs = Sound.objects.select_related("pack", "user", "license") \
                                .filter(processing_state="OK", moderation_state="OK")
        add_all_sounds_to_solr(sound_qs)
