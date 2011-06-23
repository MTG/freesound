from django.core.management.base import BaseCommand
from sounds.models import Sound
from utils.search.search import add_all_sounds_to_solr

class Command(BaseCommand):
    args = ''
    help = 'Add all sounds with index_dirty flag True to SOLR index'

    def handle(self, *args, **options):
        sound_qs = Sound.objects.select_related("pack", "user", "license") \
                                .filter(is_index_dirty=True,
                                        moderation_state='OK',
                                        processing_state='OK')

        add_all_sounds_to_solr(sound_qs, mark_index_clean=True)
