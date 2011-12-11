# -*- coding: utf-8 -*-
from django.contrib import admin
from accounts.models import Profile

class ProfileAdmin(admin.ModelAdmin):
    raw_id_fields = ('user', 'geotag') 
    list_display = ('user', 'home_page', 'signature', 'is_whitelisted')
    ordering = ('id', )
    list_filter = ('is_whitelisted', 'wants_newsletter', )
    search_fields = ('=user__username', )

admin.site.register(Profile, ProfileAdmin)