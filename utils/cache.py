from django.core.cache import cache
from django.utils.hashcompat import md5_constructor
from django.utils.http import urlquote
from functional import compose

def invalidate_template_cache(fragment_name, *variables):
    args = md5_constructor(u':'.join(map(compose(urlquote, unicode), variables)))
    cache_key = 'template.cache.%s.%s' % (fragment_name, args.hexdigest())
    cache.delete(cache_key) 