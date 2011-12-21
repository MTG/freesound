# -*- coding: utf-8 -*-
from django.contrib import admin
from bookmarks.models import Bookmark, BookmarkCategory

class BookmarkAdmin(admin.ModelAdmin):
    raw_id_fields = ('user','category','sound') 
    list_display = ('user', 'name', 'category', 'sound')

class BookmarkCategoryAdmin(admin.ModelAdmin):
    raw_id_fields = ('user',) 
    list_display = ('user', 'name')


admin.site.register(Bookmark, BookmarkAdmin)
admin.site.register(BookmarkCategory, BookmarkCategoryAdmin)