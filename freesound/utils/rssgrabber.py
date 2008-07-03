from django.core.cache import cache
import feedparser

def grab(url):
    key_name = 'rss_' + url
    
    cached = cache.get(key_name)
    
    if cached:
        return cached
    else:
        parsed = feedparser.parse(url)
        cache.set(key_name, parsed, 60*60)
        
        return parsed