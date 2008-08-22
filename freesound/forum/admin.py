# -*- coding: utf-8 -*-
from django.contrib import admin
from models import Category, Forum, Thread, Post

class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'change_order')

admin.site.register(Category, CategoryAdmin)
    

class ForumAdmin(admin.ModelAdmin):
    raw_id_fields = ('last_post', )
    list_display = ('name', 'num_threads', 'num_views', 'change_order')

admin.site.register(Forum, ForumAdmin)


class ThreadAdmin(admin.ModelAdmin):
    raw_id_fields = ('author', 'last_post')
    list_display = ('forum', 'author', 'title', 'status', 'num_posts', 'num_views', 'created')
    list_filters = ('status',)

admin.site.register(Thread, ThreadAdmin)


class PostAdmin(admin.ModelAdmin):
    raw_id_fields = ('author', 'thread')
    list_display = ('thread', 'author', 'num_views', 'created')

admin.site.register(Post, PostAdmin)
