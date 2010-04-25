# -*- coding: utf-8 -*-
from django.contrib import admin
from wiki.models import Page, Content

class PageAdmin(admin.ModelAdmin):
    list_display = ('name', )
admin.site.register(Page, PageAdmin)


class ContentAdmin(admin.ModelAdmin):
    raw_id_fields = ('author', )
    list_display = ('page', 'author', 'title', 'created', )
admin.site.register(Content, ContentAdmin)