# -*- coding: utf-8 -*-
from django.contrib import admin
from images.models import Image

class ImageAdmin(admin.ModelAdmin):
    raw_id_fields = ('user',) 
    list_display = ('user', 'title', 'base_filename_slug', 'created')
    search_fields = ('=user__username', )

admin.site.register(Image, ImageAdmin)