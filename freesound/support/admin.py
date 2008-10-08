# -*- coding: utf-8 -*-
from django.contrib import admin
from models import Question, StandardReply, Reply

class QuestionAdmin(admin.ModelAdmin):
    raw_id_fields = ('user', )
    list_display = ('user', 'email', 'type', 'subject', 'is_answered')
    list_filter = ('is_answered', )

admin.site.register(Question, QuestionAdmin)


class StandardReplyAdmin(admin.ModelAdmin):
    list_display = ('type', 'summary')

admin.site.register(StandardReply, StandardReplyAdmin)


class ReplyAdmin(admin.ModelAdmin):
    raw_id_fields = ('user', )
    list_display = ('user', 'question')

admin.site.register(Reply, ReplyAdmin)