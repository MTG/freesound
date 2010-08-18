# -*- coding: utf-8 -*-
from django.contrib import admin
from api.models import ApiKey

class ApiKeyAdmin(admin.ModelAdmin):
    raw_id_fields = ('user',) 
    search_fields = ('=user__username', )
    list_filter = ('status', )
    list_display = ("key", "user", "status")

admin.site.register(ApiKey, ApiKeyAdmin)