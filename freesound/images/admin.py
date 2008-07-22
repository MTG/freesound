# -*- coding: utf-8 -*-
from django.contrib import admin
from models import Image

class ImageAdmin(admin.ModelAdmin):
    raw_id_fields = ('user',) 
    list_display = ('user', 'title', 'base_filename_slug', 'content_type', 'object_id', 'created')

admin.site.register(Image, ImageAdmin)