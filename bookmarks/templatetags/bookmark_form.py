#from __future__ import absolute_import
#from sounds.models import Pack, Sound
from django import template
from bookmarks.models import BookmarkCategory, Bookmark
from django.core.urlresolvers import reverse

register = template.Library()

@register.inclusion_tag('bookmarks/bookmark_form.html', takes_context=True)
def bookmark_form(context, user, sound, next = ""):
    existing_categories = BookmarkCategory.objects.filter(user=user)
    
    try:
        bookmark = Bookmark.objects.get(user=user,sound=sound)
        bookmark_name = bookmark.name
        bookmark_id = bookmark.id
        new_bookmark = False
        bookmarked_categories_for_sound = bookmark.categories.all()
    except:
        # Sound has no categories or has not been bookmarked
        bookmarked_categories_for_sound = []
        bookmark_name = ""
        bookmark_id = False
        new_bookmark = True
    
    # Remove already bookmarked categories from existing categories
    categories = []
    for cat in existing_categories:
        if not cat in bookmarked_categories_for_sound:
            categories.append(cat)
    
    
    #if next == "sound-page":
    #    next = reverse("sound", args=[sound.user.username, sound.id])
    #elif next == "category_page":
    #    next = reverse("bookmarks-for-user-for-category", args=[user.username, category_id])
    #else:
    #    next = reverse("bookmarks-for-user", args=[user.username])
    
    return {'next':next, 'new_bookmark':new_bookmark,'bookmark_id':bookmark_id,'bookmark_name':bookmark_name,'user':user,'sound':sound,'bookmarked_categories_for_sound':bookmarked_categories_for_sound,'categories':categories,'media_url': context['media_url'],}
