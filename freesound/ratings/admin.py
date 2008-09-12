# -*- coding: utf-8 -*-
from django.contrib import admin
from models import Rating

class RatingAdmin(admin.ModelAdmin):
    raw_id_fields = ('user',)
    list_display = ('user', 'content_type', 'object_id', 'rating', 'created')
    search_fields = ('=user__username', )
    list_filter = ('rating',)

admin.site.register(Rating, RatingAdmin)