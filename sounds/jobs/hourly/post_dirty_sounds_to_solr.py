from django_extensions.management.jobs import HourlyJob
from sounds.models import Sound
from utils.search.search import add_all_sounds_to_solr

class Job(HourlyJob):
    help = "Post dirty sounds to Solr"

    def execute(self):
        sound_qs = Sound.objects.select_related("pack", "user", "license") \
                                .filter(is_index_dirty=True,
                                        moderation_state='OK',
                                        processing_state='OK')

        add_all_sounds_to_solr(sound_qs, mark_index_clean=True)