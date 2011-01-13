from sounds.models import Download
from django.core.cache import cache
from django.conf import settings
from datetime import datetime

class DBTime():
    last_time = None

    @staticmethod
    def get_last_time():
	if not settings.DEBUG:
	    return datetime.now() 
	if DBTime.last_time is None:
            cache_key = "last_download_time"
            last_time = cache.get(cache_key)
            if not last_time:
		try:
		    last_time = Download.objects.order_by('-created')[0].created
		except Download.DoesNotExist:
		    last_time = datetime.now()
		    cache.set(cache_key, DBTime.last_time, 60*60*24)
            DBTime.last_time = last_time
	return DBTime.last_time
