# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Sound.processing_ongoing_state'
        db.add_column('sounds_sound', 'processing_ongoing_state',
                      self.gf('django.db.models.fields.CharField')(default='QU', max_length=2, db_index=True),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'Sound.processing_ongoing_state'
        db.delete_column('sounds_sound', 'processing_ongoing_state')


    models = {
        'apiv2.apiv2client': {
            'Meta': {'object_name': 'ApiV2Client'},
            'accepted_tos': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'allow_oauth_passoword_grant': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'key': ('django.db.models.fields.CharField', [], {'max_length': '40', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'oauth_client': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'apiv2_client'", 'null': 'True', 'default': 'None', 'to': "orm['oauth2.Client']", 'blank': 'True', 'unique': 'True'}),
            'redirect_uri': ('django.db.models.fields.URLField', [], {'max_length': '200'}),
            'scope': ('django.db.models.fields.CharField', [], {'default': "'rw'", 'max_length': '3'}),
            'status': ('django.db.models.fields.CharField', [], {'default': "'OK'", 'max_length': '3'}),
            'throttling_level': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'apiv2_client'", 'to': "orm['auth.User']"})
        },
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
        'comments.comment': {
            'Meta': {'ordering': "('-created',)", 'object_name': 'Comment'},
            'comment': ('django.db.models.fields.TextField', [], {}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'db_index': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'related_name': "'replies'", 'null': 'True', 'blank': 'True', 'to': "orm['comments.Comment']"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'favorites.favorite': {
            'Meta': {'ordering': "('-created',)", 'unique_together': "(('user', 'content_type', 'object_id'),)", 'object_name': 'Favorite'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'db_index': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'geotags.geotag': {
            'Meta': {'object_name': 'GeoTag'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'db_index': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lat': ('django.db.models.fields.FloatField', [], {'db_index': 'True'}),
            'lon': ('django.db.models.fields.FloatField', [], {'db_index': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'zoom': ('django.db.models.fields.IntegerField', [], {})
        },
        'oauth2.client': {
            'Meta': {'object_name': 'Client'},
            'client_id': ('django.db.models.fields.CharField', [], {'default': "'1bc9a0ad4393805f4db7'", 'max_length': '255'}),
            'client_secret': ('django.db.models.fields.CharField', [], {'default': "'1804b4640c6d4b76ae026d363f39b23f7f64d273'", 'max_length': '255'}),
            'client_type': ('django.db.models.fields.IntegerField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'redirect_uri': ('django.db.models.fields.URLField', [], {'max_length': '200'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'oauth2_client'", 'null': 'True', 'to': "orm['auth.User']"})
        },
        'ratings.rating': {
            'Meta': {'ordering': "('-created',)", 'unique_together': "(('user', 'content_type', 'object_id'),)", 'object_name': 'Rating'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'db_index': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'rating': ('django.db.models.fields.IntegerField', [], {}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'sounds.deletedsound': {
            'Meta': {'object_name': 'DeletedSound'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'sound_id': ('django.db.models.fields.IntegerField', [], {'default': '0', 'db_index': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'sounds.download': {
            'Meta': {'ordering': "('-created',)", 'object_name': 'Download'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'db_index': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'pack': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'to': "orm['sounds.Pack']", 'null': 'True', 'blank': 'True'}),
            'sound': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'to': "orm['sounds.Sound']", 'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'sounds.flag': {
            'Meta': {'ordering': "('-created',)", 'object_name': 'Flag'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'db_index': 'True', 'blank': 'True'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'reason': ('django.db.models.fields.TextField', [], {}),
            'reason_type': ('django.db.models.fields.CharField', [], {'default': "'I'", 'max_length': '1'}),
            'reporting_user': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'sound': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['sounds.Sound']"})
        },
        'sounds.license': {
            'Meta': {'ordering': "['order']", 'object_name': 'License'},
            'abbreviation': ('django.db.models.fields.CharField', [], {'max_length': '8', 'db_index': 'True'}),
            'deed_url': ('django.db.models.fields.URLField', [], {'max_length': '200'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_public': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'legal_code_url': ('django.db.models.fields.URLField', [], {'max_length': '200'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '512'}),
            'order': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'summary': ('django.db.models.fields.TextField', [], {})
        },
        'sounds.pack': {
            'Meta': {'ordering': "('-created',)", 'unique_together': "(('user', 'name'),)", 'object_name': 'Pack'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'db_index': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'default': 'None', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_dirty': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'last_updated': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'db_index': 'True', 'blank': 'True'}),
            'license_crc': ('django.db.models.fields.CharField', [], {'max_length': '8', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'num_downloads': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'num_sounds': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'sounds.remixgroup': {
            'Meta': {'object_name': 'RemixGroup'},
            'group_size': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'protovis_data': ('django.db.models.fields.TextField', [], {'default': 'None', 'null': 'True', 'blank': 'True'}),
            'sounds': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'remix_group'", 'blank': 'True', 'to': "orm['sounds.Sound']"})
        },
        'sounds.sound': {
            'Meta': {'ordering': "('-created',)", 'object_name': 'Sound'},
            'analysis_state': ('django.db.models.fields.CharField', [], {'default': "'PE'", 'max_length': '2', 'db_index': 'True'}),
            'avg_rating': ('django.db.models.fields.FloatField', [], {'default': '0'}),
            'base_filename_slug': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '512', 'null': 'True', 'blank': 'True'}),
            'bitdepth': ('django.db.models.fields.IntegerField', [], {'default': 'None', 'null': 'True', 'blank': 'True'}),
            'bitrate': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'channels': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'crc': ('django.db.models.fields.CharField', [], {'max_length': '8', 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'db_index': 'True', 'blank': 'True'}),
            'date_recorded': ('django.db.models.fields.DateField', [], {'default': 'None', 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'duration': ('django.db.models.fields.FloatField', [], {'default': '0'}),
            'filesize': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'geotag': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'to': "orm['geotags.GeoTag']", 'null': 'True', 'on_delete': 'models.SET_NULL', 'blank': 'True'}),
            'has_bad_description': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_index_dirty': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'license': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['sounds.License']"}),
            'md5': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '32', 'db_index': 'True'}),
            'moderation_date': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True', 'blank': 'True'}),
            'moderation_note': ('django.db.models.fields.TextField', [], {'default': 'None', 'null': 'True', 'blank': 'True'}),
            'moderation_state': ('django.db.models.fields.CharField', [], {'default': "'PE'", 'max_length': '2', 'db_index': 'True'}),
            'num_comments': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'num_downloads': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'num_ratings': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'original_filename': ('django.db.models.fields.CharField', [], {'max_length': '512'}),
            'original_path': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '512', 'null': 'True', 'blank': 'True'}),
            'pack': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'to': "orm['sounds.Pack']", 'null': 'True', 'on_delete': 'models.SET_NULL', 'blank': 'True'}),
            'processing_date': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True', 'blank': 'True'}),
            'processing_log': ('django.db.models.fields.TextField', [], {'default': 'None', 'null': 'True', 'blank': 'True'}),
            'processing_ongoing_state': ('django.db.models.fields.CharField', [], {'default': "'QU'", 'max_length': '2', 'db_index': 'True'}),
            'processing_state': ('django.db.models.fields.CharField', [], {'default': "'PE'", 'max_length': '2', 'db_index': 'True'}),
            'samplerate': ('django.db.models.fields.FloatField', [], {'default': '0'}),
            'similarity_state': ('django.db.models.fields.CharField', [], {'default': "'PE'", 'max_length': '2', 'db_index': 'True'}),
            'sources': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'remixes'", 'blank': 'True', 'to': "orm['sounds.Sound']"}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '4', 'db_index': 'True'}),
            'uploaded_with_apiv2_client': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'to': "orm['apiv2.ApiV2Client']", 'null': 'True', 'on_delete': 'models.SET_NULL', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'sounds'", 'to': "orm['auth.User']"})
        },
        'tags.tag': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Tag'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '100'})
        },
        'tags.taggeditem': {
            'Meta': {'ordering': "('-created',)", 'unique_together': "(('tag', 'content_type', 'object_id'),)", 'object_name': 'TaggedItem'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'db_index': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'tag': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['tags.Tag']"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        }
    }

    complete_apps = ['sounds']