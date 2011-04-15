# -*- coding: utf-8 -*-
from django.contrib import admin
from geotags.models import GeoTag

class GeoTagAdmin(admin.ModelAdmin):
    search_fields = ('=user__username',)
    raw_id_fields = ('user',) 
    list_display = ('user', 'lat', 'lon', 'created')

admin.site.register(GeoTag, GeoTagAdmin)