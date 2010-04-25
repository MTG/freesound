# -*- coding: utf-8 -*-
from django.contrib import admin
from forum.models import Forum, Thread, Post

class ForumAdmin(admin.ModelAdmin):
    raw_id_fields = ('last_post', )
    list_display = ('name', 'num_threads', 'change_order')

admin.site.register(Forum, ForumAdmin)


class ThreadAdmin(admin.ModelAdmin):
    raw_id_fields = ('author', 'last_post')
    list_display = ('forum', 'author', 'title', 'status', 'num_posts', 'created')
    list_filters = ('status',)
    search_fields = ('=author__username', "title")

admin.site.register(Thread, ThreadAdmin)


class PostAdmin(admin.ModelAdmin):
    raw_id_fields = ('author', 'thread')
    list_display = ('thread', 'author', 'created')
    search_fields = ('=author__username', "body")

admin.site.register(Post, PostAdmin)
