# -*- coding: utf-8 -*-
from django.contrib import admin
from tags.models import Tag, TaggedItem

class TagAdmin(admin.ModelAdmin):
    list_display = ('tag',)

admin.site.register(Tag)

class TaggedItemAdmin(admin.ModelAdmin):
    search_fields = ('=tag__name',)
    raw_id_fields = ('user', 'tag')
    list_display = ('user', 'content_type', 'object_id', 'tag', 'created')

admin.site.register(TaggedItem, TaggedItemAdmin)