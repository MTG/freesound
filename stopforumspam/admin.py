from django.contrib import admin
import models

class LogAdmin(admin.ModelAdmin):
    list_display = ('inserted', 'message')
    list_filter = ('inserted',)

class CacheAdmin(admin.ModelAdmin):
    list_display = ('ip', 'updated')
    list_filter = ('permanent', 'updated')
    

site = admin.site.register(models.Log, LogAdmin)
site = admin.site.register(models.Cache, CacheAdmin)
