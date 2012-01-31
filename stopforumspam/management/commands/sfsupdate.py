from django.db import transaction
from django.core.management.base import BaseCommand
from datetime import datetime

from stopforumspam import models
from stopforumspam import settings as sfs_settings

import re
import urllib
import zipfile
from optparse import make_option

class Command(BaseCommand):
    args = '--force'
    help = 'Updates the database with the latest IPs from stopforumspam.com'
    option_list = BaseCommand.option_list + (
        make_option('--force', '-f', dest='force', default=False,
                    action='store_true',
                    help='Force update of options'),
        )
    
    def handle(self, *args, **options):
        self.ensure_updated(options['force'])
        
    def ensure_updated(self, force=False):
        last_update = models.Log.objects.filter(message=sfs_settings.LOG_MESSAGE_UPDATE)
        do_update = force
        if not do_update and last_update.count() > 0:
            days_ago = datetime.now() - last_update
            if days_ago.days >= sfs_settings.CACHE_EXPIRE:
                do_update = True
        else:
            do_update = True
        if do_update:
            print "Updating (this may take some time)"
            print "If you abort this command and want to rebuild, you have to use the --force option!"
            self.do_update()
        else:
            print "Nothing to update"
    
    
    @transaction.commit_manually
    def do_update(self):

        # Delete old cache
        models.Cache.objects.filter(permanent=False).delete()
        transaction.commit()
        
        # First log the update
        log = models.Log()
        log.message = sfs_settings.LOG_MESSAGE_UPDATE
        log.save()
        
        # For security purposes we test that each line is actually an IP address
        ip_match = re.compile(r"^(\d+)\.(\d+)\.(\d+)\.(\d+)$")
        
        filename, __ = urllib.urlretrieve(sfs_settings.SOURCE_ZIP)
        z = zipfile.ZipFile(filename)
        ips = z.read(sfs_settings.ZIP_FILENAME)
        ips = ips.split("\n")
        ips = filter(lambda x: ip_match.match(x), ips)
        inserted = 0
        total = len(ips)
        for ip in ips:
            cache = models.Cache(ip=ip)
            cache.save()
            inserted = inserted + 1
            if inserted % 100 == 0:
                print "Inserted %d of %d" % (inserted, total)
        
        transaction.commit()

    