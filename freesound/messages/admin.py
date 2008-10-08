# -*- coding: utf-8 -*-
from django.contrib import admin
from models import Message, MessageBody

class MessageAdmin(admin.ModelAdmin):
    raw_id_fields = ('user_from', 'user_to', 'body')
    list_display = ('user_from', 'user_to', 'subject', 'is_sent', 'is_read', 'is_archived', 'created', )
    search_fields = ('=user_from__username', '=user_to__username', 'subject',)
    list_filter = ('is_sent', 'is_read', 'is_archived', )

admin.site.register(Message, MessageAdmin)

admin.site.register(MessageBody)