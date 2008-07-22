# -*- coding: utf-8 -*-
from django.contrib import admin
from models import Tag, TaggedItem

admin.site.register(Tag)

class TaggedItemAdmin(admin.ModelAdmin):
    raw_id_fields = ('user', )
    list_display = ('user', 'content_type', 'object_id', 'tag', 'created')

admin.site.register(TaggedItem, TaggedItemAdmin)