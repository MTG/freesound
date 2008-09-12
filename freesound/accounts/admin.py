# -*- coding: utf-8 -*-
from django.contrib import admin
from models import Profile

class ProfileAdmin(admin.ModelAdmin):
    raw_id_fields = ('user', ) 
    list_display = ('user', 'home_page', 'signature', 'whitelisted')
    ordering = ('user__username', )
    list_filter = ('whitelisted', 'newsletter', )
    search_fields = ('=user__username', )

admin.site.register(Profile, ProfileAdmin)