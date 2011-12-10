# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'Queue'
        db.create_table('tickets_queue', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=128)),
            ('notify_by_email', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal('tickets', ['Queue'])

        # Adding M2M table for field groups on 'Queue'
        db.create_table('tickets_queue_groups', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('queue', models.ForeignKey(orm['tickets.queue'], null=False)),
            ('group', models.ForeignKey(orm['auth.group'], null=False))
        ))
        db.create_unique('tickets_queue_groups', ['queue_id', 'group_id'])

        # Adding model 'LinkedContent'
        db.create_table('tickets_linkedcontent', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('content_type', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['contenttypes.ContentType'])),
            ('object_id', self.gf('django.db.models.fields.PositiveIntegerField')(db_index=True)),
        ))
        db.send_create_signal('tickets', ['LinkedContent'])

        # Adding model 'Ticket'
        db.create_table('tickets_ticket', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=256)),
            ('source', self.gf('django.db.models.fields.CharField')(max_length=128)),
            ('status', self.gf('django.db.models.fields.CharField')(max_length=128)),
            ('key', self.gf('django.db.models.fields.CharField')(default='89d5bf95dc95492fbf46519289d105ba', max_length=32, db_index=True)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, db_index=True, blank=True)),
            ('modified', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('sender', self.gf('django.db.models.fields.related.ForeignKey')(related_name='sent_tickets', null=True, to=orm['auth.User'])),
            ('sender_email', self.gf('django.db.models.fields.EmailField')(max_length=75, null=True)),
            ('assignee', self.gf('django.db.models.fields.related.ForeignKey')(related_name='assigned_tickets', null=True, to=orm['auth.User'])),
            ('queue', self.gf('django.db.models.fields.related.ForeignKey')(related_name='tickets', to=orm['tickets.Queue'])),
            ('content', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['tickets.LinkedContent'], null=True)),
        ))
        db.send_create_signal('tickets', ['Ticket'])

        # Adding model 'TicketComment'
        db.create_table('tickets_ticketcomment', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('sender', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'], null=True)),
            ('text', self.gf('django.db.models.fields.TextField')()),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('ticket', self.gf('django.db.models.fields.related.ForeignKey')(related_name='messages', to=orm['tickets.Ticket'])),
            ('moderator_only', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal('tickets', ['TicketComment'])

        # Adding model 'UserAnnotation'
        db.create_table('tickets_userannotation', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('sender', self.gf('django.db.models.fields.related.ForeignKey')(related_name='sent_annotations', to=orm['auth.User'])),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(related_name='annotations', to=orm['auth.User'])),
            ('text', self.gf('django.db.models.fields.TextField')()),
        ))
        db.send_create_signal('tickets', ['UserAnnotation'])


    def backwards(self, orm):
        
        # Deleting model 'Queue'
        db.delete_table('tickets_queue')

        # Removing M2M table for field groups on 'Queue'
        db.delete_table('tickets_queue_groups')

        # Deleting model 'LinkedContent'
        db.delete_table('tickets_linkedcontent')

        # Deleting model 'Ticket'
        db.delete_table('tickets_ticket')

        # Deleting model 'TicketComment'
        db.delete_table('tickets_ticketcomment')

        # Deleting model 'UserAnnotation'
        db.delete_table('tickets_userannotation')


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'tickets.linkedcontent': {
            'Meta': {'object_name': 'LinkedContent'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'})
        },
        'tickets.queue': {
            'Meta': {'object_name': 'Queue'},
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'notify_by_email': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        },
        'tickets.ticket': {
            'Meta': {'ordering': "('-created',)", 'object_name': 'Ticket'},
            'assignee': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'assigned_tickets'", 'null': 'True', 'to': "orm['auth.User']"}),
            'content': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['tickets.LinkedContent']", 'null': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'db_index': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'key': ('django.db.models.fields.CharField', [], {'default': "'cf777fc0f0f14330a483acfd847b4c61'", 'max_length': '32', 'db_index': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'queue': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'tickets'", 'to': "orm['tickets.Queue']"}),
            'sender': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'sent_tickets'", 'null': 'True', 'to': "orm['auth.User']"}),
            'sender_email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'null': 'True'}),
            'source': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'status': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '256'})
        },
        'tickets.ticketcomment': {
            'Meta': {'ordering': "('-created',)", 'object_name': 'TicketComment'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'moderator_only': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'sender': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True'}),
            'text': ('django.db.models.fields.TextField', [], {}),
            'ticket': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'messages'", 'to': "orm['tickets.Ticket']"})
        },
        'tickets.userannotation': {
            'Meta': {'object_name': 'UserAnnotation'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'sender': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'sent_annotations'", 'to': "orm['auth.User']"}),
            'text': ('django.db.models.fields.TextField', [], {}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'annotations'", 'to': "orm['auth.User']"})
        }
    }

    complete_apps = ['tickets']
