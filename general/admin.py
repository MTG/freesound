# -*- coding: utf-8 -*-
from django.contrib import admin
from general.models import AkismetSpam

class AkismetSpamAdmin(admin.ModelAdmin):
    raw_id_fields = ('user', ) 
    list_display = ('user', 'created')
    ordering = ('-created', )
    search_fields = ('=user__username', )

admin.site.register(AkismetSpam, AkismetSpamAdmin)