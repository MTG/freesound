#
# Freesound is (c) MUSIC TECHNOLOGY GROUP, UNIVERSITAT POMPEU FABRA
#
# Freesound is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# Freesound is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# Authors:
#     See AUTHORS file.
#

import json
import logging
import os
import uuid

from django.core.cache import caches
from fabric import Connection

from sounds.models import Sound
from utils.management_commands import LoggingBaseCommand

console_logger = logging.getLogger('console')
cache_cdn_map = caches["cdn_map"]
cdn_host = 'fsweb@cdn.freesound.org'
cdn_sounds_dir = '/home/fsweb/sounds'
cdn_symlinks_dir = '/home/fsweb/symlinks'
tmp_dest_sound_dir =  '/home/fsweb/tmp/'


class Command(LoggingBaseCommand):

    help = 'Update the CDN map cache for sound downloads by copying new files to the remote CDN or using a JSON file with updated mapping'

    def add_arguments(self, parser):
        parser.add_argument('-f', '--filepath', dest='filepath', type=str, help='Path to JSON file with sounds map. If using this option, no new sounds will be copied to the CDN but only the local map in cache will be updated')
        parser.add_argument('-k', '--keypath', dest='keypath', default='/root/.ssh/id_rsa', type=str, help='Path to the SSH private key to use for connecting to CDN')
        parser.add_argument('-d', help='Clear the existing records in the cache (if any) and don\'t do anything else')
        parser.add_argument('-l', action='store', dest='limit', default=500, help='Maximum number of sounds to copy to remote CDN and update cache')
        
    def handle(self, *args, **options):

        self.log_start()

        file_path = options['filepath']
        ssh_key_path = options['keypath']
        delete_already_existing = options['d']       
        limit = options['limit'] 
        num_added = 0
        num_failed = 0

        if delete_already_existing:
            cache_cdn_map.clear()
        else:
            if file_path:
                # If file path, simply update the redis cache with the data form the file and don't do anything else
                console_logger.info('Adding cache items from file {}'.format(file_path))
                map_data = json.load(open(file_path))
                for sound_id, cdn_filename in map_data:
                    cache_cdn_map.set(str(sound_id), cdn_filename, timeout=None)  # No expiration
                    num_added = len(map_data)
            else:
                console_logger.info('Finding new sounds to add to the cache')
                # Find sounds which are not in cache
                # To do that, we get all sounds with IDs higher than the highest sound ID in the cache
                keys = cache_cdn_map.keys('*')
                int_keys = [int(key) for key in keys]
                if int_keys:
                    highest_sound_id_in_cache = max(int_keys)
                else:
                    highest_sound_id_in_cache = 0

                all_ss = Sound.objects.filter(id__gt=highest_sound_id_in_cache).order_by('id')
                ss = all_ss[:limit]
                total = ss.count()
                console_logger.info('Found {} new sounds missing in the cache, will add first {}'.format(all_ss.count(), total))
                
                # Copy sounds if not already there, make symlinks and add them to cache
                with Connection(host=cdn_host, connect_kwargs={'key_filename': ssh_key_path}) as c:
                    for count, sound in enumerate(ss):
                        # Define useful paths for that sound
                        sound_id = sound.id
                        src_sound_path = sound.locations('path')
                        folder_id = str(sound.id//1000)
                        dst_sound_path = os.path.join(cdn_sounds_dir, folder_id,  os.path.basename(src_sound_path))
                        console_logger.info('Adding sound to the CDN [{}/{}] - {}'.format(count + 1, total, sound_id))

                        # Check if sound already exists in the expected remote location    
                        sound_exists = c.run('ls {}'.format(dst_sound_path), hide=True, warn=True).exited == 0
                        if not sound_exists:
                            # Copy file to remote, make intermediate folders if needed
                            c.run('mkdir -p {}'.format(os.path.dirname(dst_sound_path)))
                            tmp_dst_sound_path = os.path.join(tmp_dest_sound_dir, os.path.basename(src_sound_path))
                            os.system('scp -o StrictHostKeyChecking=no {} {}:{}'.format(src_sound_path, cdn_host, tmp_dst_sound_path))
                            os.system('ssh {} sudo mv {} {}'.format(cdn_host, tmp_dst_sound_path, dst_sound_path))
                            # NOTE: for some reason c.put has permission issues and can't put files as fsweb (fsweb can't write to sounds
                            # folder in /home/fsweb). We need to use scp as root to be able to copy files and then use sudo mv from fsweb user.
                            # If we fix fsweb permissions in CDN, then we can simply use c.put(src_sound_path, dst_sound_path)

                        # Make symlink (remove previously existing symlinks for that sound if any already exists)
                        # Before making the symlink, check again that sound exists, otherwise don't make it as there were problems copying sound
                        sound_exists = c.run('ls {}'.format(dst_sound_path), hide=True, warn=True).exited == 0
                        if sound_exists:
                            c.run('rm {}'.format(os.path.join(cdn_symlinks_dir, folder_id,  '{}-*'.format(sound_id))), hide=True, warn=True)
                            random_uuid = str(uuid.uuid4())
                            symlink_name = '{}-{}'.format(sound_id, random_uuid)
                            dst_symlink_path = os.path.join(cdn_symlinks_dir, folder_id,  symlink_name)
                            c.run('mkdir -p {}'.format(os.path.dirname(dst_symlink_path)))
                            c.run('ln -s {} {}'.format(dst_sound_path, dst_symlink_path))

                            # Fill cache
                            # Before filling the cache, make sure symlink exists (has been cretated successfully), otherwise do not fill the cache
                            # as there were problems creating the symlink
                            symlink_exists = c.run('ls {}'.format(dst_symlink_path), hide=True, warn=True).exited == 0
                            if symlink_exists:
                                cache_cdn_map.set(str(sound_id), symlink_name, timeout=None)  # No expiration
                                num_added += 1
                            else:
                                num_failed += 1
                        else:
                            num_failed += 1

        console_logger.info('Done! Added {} items to cache ({} failed)'.format(num_added, num_failed))
        self.log_end({'added_to_cache': num_added, 'failed_adding_to_cache': num_failed})
