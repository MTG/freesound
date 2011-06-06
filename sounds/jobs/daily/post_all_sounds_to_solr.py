from django_extensions.management.jobs import DailyJob
from sounds.models import Sound
from utils.search.search import add_all_sounds_to_solr

class Job(DailyJob):
    help = "Post all sounds to solr"

    def execute(self):
        sound_qs = Sound.objects.select_related("pack", "user", "license") \
                                .filter(processing_state="OK", moderation_state="OK")
        add_all_sounds_to_solr(sound_qs)
