# -*- coding: utf-8 -*-
from django.contrib import admin
from models import Comment

class CommentAdmin(admin.ModelAdmin):
    raw_id_fields = ('user',) 
    list_display = ('user', 'content_type', 'object_id', 'created')
    search_fields = ('comment', )

admin.site.register(Comment, CommentAdmin)