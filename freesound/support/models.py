# -*- coding: utf-8 -*-
from django.contrib import admin
from django.utils.translation import ugettext as _
from django.contrib.auth.models import User
from django.db import models

QUESTION_TYPE_CHOICES = (
    ('P', _('User registration, activation, ...')),
    ('L', _('Legal help, license, ...')),
    ('T', _('Technical question')),
    ('O', _('Other')),
)

# Create your models here.
class Question(models.Model):
    user = models.ForeignKey(User, null=True, blank=True, default=None)
    email = models.EmailField(null=True, blank=True, default=None)

    type = models.CharField(db_index=True, max_length=1, choices=QUESTION_TYPE_CHOICES)
    subject = models.TextField(null=True, blank=True, default=None)
    question = models.TextField()
    
    answered = models.BooleanField()
    created = models.DateTimeField()
    
    def __unicode__(self):
        return u"%s - %s: %s - %s answered: %s" % (self.user, self.email, self.type, self.subject, self.answered)

class QuestionAdmin(admin.ModelAdmin):
    raw_id_fields = ('user', )
    list_display = ('user', 'email', 'type', 'subject', 'answered')
    list_filter = ('answered', )
admin.site.register(Question, QuestionAdmin)


class StandardReply(models.Model):
    type = models.CharField(db_index=True, max_length=1, choices=QUESTION_TYPE_CHOICES)
    summary = models.CharField(max_length=128)
    reply = models.TextField()

    def __unicode__(self):
        return u"%s %s" % (self.type, self.summary)

    class Meta:
        unique_together = ('type', 'summary')

class StandardReplyAdmin(admin.ModelAdmin):
    list_display = ('type', 'summary')
admin.site.register(StandardReply, StandardReplyAdmin)


class Reply(models.Model):
    user = models.ForeignKey(User)

    question = models.OneToOneField(Question)
    reply = models.TextField()
    standard_rely = models.OneToOneField(StandardReply, null=True, blank=True, default=None, related_name="standard_reply")
    
    created = models.DateTimeField()

class ReplyAdmin(admin.ModelAdmin):
    raw_id_fields = ('user', )
    list_display = ('user', 'question')
admin.site.register(Reply, ReplyAdmin)