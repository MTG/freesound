# Generated by Django 3.2.17 on 2023-03-28 12:05

from django.db import migrations


def init_new_sound_pack_download_counts(apps, schema_editor):
    
    Profile = apps.get_model('accounts', 'Profile')
    Download = apps.get_model('sounds', 'Download')
    PackDownload = apps.get_model('sounds', 'PackDownload')

    qs = Profile.objects.filter(num_sounds__gt=0).all().only('user_id')
    total = qs.count()
    for count, profile in enumerate(qs):
        profile.num_user_sounds_downloads = Download.objects.filter(sound__user_id=profile.user_id).count() 
        profile.num_user_packs_downloads = PackDownload.objects.filter(pack__user_id=profile.user_id).count()
        profile.save()
        if count % 1000 == 0:
            print(f'[{count + 1}/{total}]')


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0039_auto_20230328_1114'),
        ('sounds', '0049_license_summary_for_describe_form'),
    ]

    operations = [
        migrations.RunPython(init_new_sound_pack_download_counts, migrations.RunPython.noop),
    ]
