#from __future__ import absolute_import
#from sounds.models import Pack, Sound
from django import template
from bookmarks.models import BookmarkCategory, Bookmark
from bookmarks.forms import BookmarkForm
from django.core.urlresolvers import reverse

register = template.Library()

@register.inclusion_tag('bookmarks/bookmark_form.html', takes_context=True)
def bookmark_form(context, request_user, sound, next = ""):
    existing_categories = BookmarkCategory.objects.filter(user=request_user)
    bookmarks = Bookmark.objects.filter(user=request_user,sound=sound)
    
    bookmarked_categories_for_sound = []
    for bookmark in bookmarks:
        if bookmark.category:
            bookmarked_categories_for_sound.append(bookmark.category)
    
    # Remove already bookmarked categories from existing categories
    possible_new_categories = []
    for cat in existing_categories:
        if not cat in bookmarked_categories_for_sound:
            possible_new_categories.append(cat)
    
    return {'next':next,'request_user':request_user,'bookmarks': bookmarks.count() != 0,'sound':sound,'bookmarked_categories_for_sound':bookmarked_categories_for_sound,'possible_new_categories':possible_new_categories,'media_url': context['media_url'],}
