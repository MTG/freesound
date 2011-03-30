# -*- coding: utf-8 -*-
from django.contrib import admin
from models import Queue, Ticket

class QueueAdmin(admin.ModelAdmin): 
    list_display = ('name',)

admin.site.register(Queue, QueueAdmin)


class TicketAdmin(admin.ModelAdmin):
    #raw_id_fields = ('content__object_id', ) 
    list_display = ('id', 'key', 'assignee', 'sender')

admin.site.register(Ticket, TicketAdmin)