# -*- coding: utf-8 -*-
from django.contrib import admin
from models import Message

class MessageAdmin(admin.ModelAdmin):
    raw_id_fields = ('user_from', 'user_to', )
    list_display = ('user_from', 'user_to', 'subject', 'read', 'deleted', 'created', )
    search_fields = ('=user_from__username', '=user_to__username', 'subject',)
    list_filter = ('read', 'deleted', )

admin.site.register(Message, MessageAdmin)