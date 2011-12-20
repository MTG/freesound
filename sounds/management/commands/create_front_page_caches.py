from django.core.management.base import NoArgsCommand
from django.conf import settings
from django.template.loader import render_to_string
from django.core.cache import cache

class Command(NoArgsCommand):
    help = "Create front page RSS and Pledgie cache."

    def handle(self, **options):
        rss_url = settings.FREESOUND_RSS
        pledgie_campaign = settings.PLEDGIE_CAMPAIGN
        
        rss_cache = render_to_string('rss_cache.html', locals())
        cache.set("rss_cache", rss_cache, 2592000) # 30 days cache

        pledgie_cache = render_to_string('pledgie_cache.html', locals())
        cache.set("pledgie_cache", pledgie_cache, 2592000) # 30 days cache