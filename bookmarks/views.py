from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.contrib.auth.models import User
from sounds.models import Sound
from bookmarks.models import *
from bookmarks.forms import BookmarkCategoryForm
from django.http import HttpResponseRedirect
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from datetime import datetime
from django.contrib import messages
from utils.pagination import paginate
from utils.functional import combine_dicts

def bookmarks(request, username, category_id = None):
    
    if request.user.username == username:
        owner = True
        user = request.user
    else:
        user = get_object_or_404(User,username = username)
    
    
    if request.POST:
        if "create_cat" in request.POST:
            form_bookmark_category = BookmarkCategoryForm(request.POST)
            if form_bookmark_category.is_valid():
                new_bookmark_category = BookmarkCategory(user=user, name=form_bookmark_category.cleaned_data["name"])
                new_bookmark_category.save()
            form_bookmark_category = BookmarkCategoryForm()
        if "action" in request.POST:
            action_type = request.POST["actions_list"]
            if request.POST["list_ids"] != "" and request.POST["list_ids"] != "[]": 
                bookmark_ids = [int(id) for id in request.POST["list_ids"].split(',')]
            else:
                bookmark_ids = []
                
            if action_type == "del":
                for id in bookmark_ids:
                    bookmark = Bookmark.objects.get(id=id)
                    sound_name = bookmark.sound.original_filename
                    bookmark.delete()
                    msg = "Deleted bookmark for sound \"" + sound_name + "\"."
                    messages.add_message(request, messages.WARNING, msg)
                   
            elif action_type[0:8] == "add_cat_":
                cat_id = int(action_type[8:])
                category_to_add = get_object_or_404(BookmarkCategory, id = cat_id)
                
                for id in bookmark_ids:
                    bookmark = get_object_or_404(Bookmark, id =id)
                    bookmark.categories.add(category_to_add)
                    sound_name = bookmark.sound.original_filename
                    msg = "Added bookmark for sound \"" + sound_name + "\" to category \"" + category_to_add.name + "\"."
                    messages.add_message(request, messages.WARNING, msg)
                    
            elif action_type[0:8] == "rem_cat_":
                cat_id = int(action_type[8:])
                category_to_remove = get_object_or_404(BookmarkCategory, id = cat_id)
                
                for id in bookmark_ids:
                    bookmark = get_object_or_404(Bookmark, id =id)
                    bookmark.categories.remove(category_to_remove)
                    sound_name = bookmark.sound.original_filename
                    msg = "Removed bookmark for sound \"" + sound_name + "\" from category \"" + category_to_remove.name + "\"."
                    messages.add_message(request, messages.WARNING, msg)
    else:
        form_bookmark_category = BookmarkCategoryForm()
    
    are_bookmarks = Bookmark.objects.select_related("sound").filter(user=user).exists()
    n_all = Bookmark.objects.select_related("sound").filter(user=user).count()
    n_uncat = Bookmark.objects.select_related("sound").filter(user=user,categories=None).count()
    
    if not category_id:
        path_parts = str(request.path).split('/')
        if "uncategorized" in path_parts:
            bookmarked_sounds = Bookmark.objects.select_related("sound").filter(user=user,categories=None)
            uncategorized = True
        else:
            bookmarked_sounds = Bookmark.objects.select_related("sound").filter(user=user)
            all = True
    else:
        category = get_object_or_404(BookmarkCategory,id=category_id,user=user)
        bookmarked_sounds = category.bookmarks.select_related("sound").all()
    
    bookmark_categories = BookmarkCategory.objects.filter(user=user)
    
    return render_to_response('bookmarks/bookmarks.html', combine_dicts(locals(),paginate(request, bookmarked_sounds, 30)), context_instance=RequestContext(request))

@login_required
def delete_bookmark_category(request, username, category_id):
    category = get_object_or_404(BookmarkCategory,id=category_id, user__username=username)
    if request.user.username == username:
        category.delete()
    
    next = request.GET.get("next","")
    if next:
        return HttpResponseRedirect(next)
    else:
        return HttpResponseRedirect(reverse("bookmarks-for-user", args=[username]))

@login_required
def delete_bookmark_from_category(request, username, category_id, bookmark_id):

    bookmark = get_object_or_404(Bookmark, id = bookmark_id)
    category = get_object_or_404(BookmarkCategory, id = category_id)
    if request.user.username == username:
        
        bookmark.categories.remove(category)
        #new_categories = []
        #for cat in bookmark.categories.all():
        #    if cat.id != int(category_id):
        #        new_categories.append(cat)
                
        #bookmark.categories = new_categories
        bookmark.save()
    
    next = request.GET.get("next","")
    if next:
        return HttpResponseRedirect(next)
    else:
        return HttpResponseRedirect(reverse("bookmarks-for-user", args=[username]))

@login_required
def add_bookmark(request, username, sound_id):
    
    category_id = -1
    if request.POST:
        category_id = int(request.POST["categories_list"])
        category_name = request.POST["cat_name"]
        name = request.POST["name"]
    else:
        name = ""
        category_name = ""
    
    if category_id != -1:
        if category_id != -2:
            category = get_object_or_404(BookmarkCategory,id=category_id, user=request.user)
        else:
            if category_name != "":
                category = BookmarkCategory(user=request.user, name=category_name)
                category.save()
            else:
                category_id = -1
            
    sound = Sound.objects.get(id=sound_id)
    
    if Bookmark.objects.filter(user=request.user,sound=sound).exists():
        bookmark = Bookmark.objects.get(user=request.user,sound=sound)
        
        bookmark.name = name
        bookmark.save()
        
        if category_id != -1:
            category.bookmarks.add(bookmark)
            category.save()
        
        msg = "Bookmark for sound \"" + sound.original_filename + "\" successfully updated."
        messages.add_message(request, messages.WARNING, msg)
            
    else:
        bookmark = Bookmark(user=request.user,sound=sound)
        
        bookmark.name = name
        bookmark.save()
        
        if category_id != -1:
            category.bookmarks.add(bookmark)
            category.save()
        
        msg = "Added new bookmark for sound \"" + sound.original_filename + "\"."
        messages.add_message(request, messages.WARNING, msg)
        
    
    next = request.GET.get("next","")
    if next:
        return HttpResponseRedirect(next)
    else:
        return HttpResponseRedirect(reverse("bookmarks-for-user", args=[username]))

@login_required
def add_to_my_bookmarks(request, username, sound_id):
    return HttpResponseRedirect(reverse("add-bookmark", args=[request.user.username, sound_id]))
    
@login_required
def delete_bookmark(request, username, bookmark_id):
    
    if request.user.username == username:
        bookmark = Bookmark.objects.get(id=bookmark_id)
        sound_name = bookmark.sound.original_filename
        bookmark.delete()
        msg = "Deleted bookmark for sound \"" + sound_name + "\"."
        messages.add_message(request, messages.WARNING, msg)
    
    next = request.GET.get("next","")
    if next:
        return HttpResponseRedirect(next)
    else:
        return HttpResponseRedirect(reverse("bookmarks-for-user", args=[username]))