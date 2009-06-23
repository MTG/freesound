from django.utils.http import urlquote
from django.core.cache import cache
from django.utils.hashcompat import md5_constructor

def invalidate_template_cache(fragment_name, *variables):
    args = md5_constructor(u':'.join(variables))
    cache_key = 'template.cache.%s.%s' % (fragment_name, args.hexdigest())
    cache.delete(cache_key)
