from datetime import timedelta, datetime
from django.core.cache import cache
from django.contrib.sites.models import Site

ONLINE_MINUTES = 10
CACHE_KEY = '%s_online_user_ids' % Site.objects.get_current().domain

_last_purged = datetime.now()

def get_online_users():
    user_dict = cache.get(CACHE_KEY)
    return hasattr(user_dict, 'keys') and user_dict.keys() or []

def cache_online_users(request):
        if request.user.is_anonymous():
            return
        user_dict = cache.get(CACHE_KEY)
        if not user_dict:
            user_dict = {}
        now = datetime.now()
        user_dict[request.user.id] = now
        # purge
        global _last_purged
        if _last_purged + timedelta(minutes=ONLINE_MINUTES) < now:
            purge_older_than = now - timedelta(minutes=ONLINE_MINUTES)
            for user_id, last_seen in user_dict.items():
                if last_seen < purge_older_than:
                    del(user_dict[user_id])
            _last_purged = now

        cache.set(CACHE_KEY, user_dict, 60*60*24)
