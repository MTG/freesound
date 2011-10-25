from django.core.paginator import Paginator, InvalidPage
from django.core.cache import cache
import hashlib

# count caching solution from http://timtrueman.com/django-pagination-count-caching/
class CachedCountProxy(object):
    ''' This allows us to monkey-patch count() on QuerySets so we can cache it and speed things up.
    '''

    def __init__(self, queryset):
        self._queryset = queryset
        self._queryset._original_count = self._queryset.count
        self._sql = self._queryset.query.get_compiler(self._queryset.db).as_sql()
        self._sql = self._sql[0] % self._sql[1]

    def __call__(self):
        ''' 1. Check cache
            2. Return cache if it's set
            3. If it's not set, call super and get the count
            4. Cache that for X seconds
        '''
        key = "paginator_count_%s" % hashlib.sha224(self._sql).hexdigest()
        count = cache.get(key)
        if count is None:
            count = self._queryset._original_count()
            cache.set(key, count, 300)
        return count

def paginate(request, qs, items_per_page=20, page_get_name='page', cache_count=False):
    # monkeypatch solution to cache the count for performance
    # disabled for now, causes problems on comments.
    if cache_count:
        qs.count = CachedCountProxy(qs)

    paginator = Paginator(qs, items_per_page)

    try:
        current_page = int(request.GET.get(page_get_name, 1))
    except ValueError:
        current_page = 1
    try:
        page = paginator.page(current_page)
    except InvalidPage:
        page = paginator.page(1)
        current_page = 1

    return dict(paginator=paginator, current_page=current_page, page=page)
