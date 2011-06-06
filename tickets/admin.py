# -*- coding: utf-8 -*-
from django.contrib import admin
from models import Queue, Ticket

class QueueAdmin(admin.ModelAdmin): 
    list_display = ('name',)

admin.site.register(Queue, QueueAdmin)


class TicketAdmin(admin.ModelAdmin):
    raw_id_fields = ('sender', 'assignee') 
    list_display = ('id', 'source', 'status', 'assignee', 'sender')

admin.site.register(Ticket, TicketAdmin)