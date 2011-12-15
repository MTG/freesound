#from __future__ import absolute_import
#from sounds.models import Pack, Sound
from django import template
from bookmarks.models import BookmarkCategory, Bookmark
from django.core.urlresolvers import reverse

register = template.Library()

@register.inclusion_tag('bookmarks/bookmark_form.html', takes_context=True)
def bookmark_form(context, request_user, sound, next = ""):
    categories = BookmarkCategory.objects.filter(user=request_user)
    bookmarks = Bookmark.objects.filter(user=request_user,sound=sound)
    
    bookmarked_categories_for_sound = []
    for bookmark in bookmarks:
        if bookmark.category:
            if bookmark.category not in bookmarked_categories_for_sound:
                bookmarked_categories_for_sound.append(bookmark.category)
    
    return {'next':next,'request_user':request_user,'bookmarks': bookmarks.count() != 0,'sound':sound,'bookmarked_categories_for_sound':bookmarked_categories_for_sound,'categories':categories,'media_url': context['media_url'],}
