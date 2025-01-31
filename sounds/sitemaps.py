from django.contrib.sitemaps import Sitemap
from sounds.models import Sound, Pack

class SoundSitemap(Sitemap):
    def get_latest_lastmod(self):
        latest_sound = Sound.public.order_by('-created').first()
        if latest_sound:
            return latest_sound.created
        return None

    def items(self):
        return Sound.public.select_related('user').all()

    def lastmod(self, obj: Sound):
        return obj.created
    
class PackSitemap(Sitemap):
    def get_latest_lastmod(self):
        latest_pack = Pack.objects.filter(is_deleted=False).order_by('-last_updated').first()
        if latest_pack:
            return latest_pack.last_updated
        return None

    def items(self):
        return Pack.objects.filter(is_deleted=False).select_related('user').all()

    def lastmod(self, obj: Pack):
        return obj.last_updated


sitemaps = {
    'sounds': SoundSitemap,
    'packs': PackSitemap,
}
