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

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.conf import settings
from sounds.models import Sound, Pack, License
from utils.audioprocessing import get_sound_type
from geotags.models import GeoTag
from utils.filesystem import md5file
from utils.text import slugify
import shutil,os,csv

class Command(BaseCommand):
    args = ''
    help = 'Upload many sounds at once'

    def handle(self, *args, **options):
        sound_list = args[0]
        base_dir = os.path.dirname(sound_list)
        delete_already_existing = False
        if len(args) > 1:
            delete_already_existing = bool(args[1])

        isHeader = True
        for line in csv.reader(open(sound_list,'rU')):
            if isHeader:
                isHeader = False
                continue

            # 0 get data from csv
            pathf,namef,tagsf,geotagf,descriptionf,licensef,packnamef,usernamef = line
            u = User.objects.get(username=usernamef)

            # 1 create dir and move sound to dir
            directory = os.path.join(settings.UPLOADS_PATH, str(u.id))
            if not os.path.exists(directory):
                os.mkdir(directory)
            src_path = base_dir + "/"+ pathf
            dest_path = os.path.join(directory, os.path.basename(pathf))
            #print src_path,dest_path

            shutil.copy(src_path,dest_path)

            # 2 make sound object
            # user id (search), original_fname(name),path (new), filesize,type,slicense
            sound = Sound()
            sound.user = u
            sound.original_filename = namef
            sound.original_path = dest_path
            sound.filesize = os.path.getsize(sound.original_path)
            sound.type = get_sound_type(sound.original_path)
            # License format
            # name: 'Creative Commons 0'
            # name: 'Attribution'
            # name: 'Attribution Noncommercial'
            l = License.objects.get(name=licensef)
            sound.license = l

            # 3 md5, check
            try:
                sound.md5 = md5file(sound.original_path)
            except IOError:
                #messages.add_message(request, messages.ERROR, 'Something went wrong with accessing the file %s.' % sound.original_path)
                continue

            sound_already_exists = Sound.objects.filter(md5=sound.md5).exists()
            if sound_already_exists:
                if delete_already_existing:
                    existing_sound = Sound.objects.get(md5=sound.md5)
                    existing_sound.delete()
                    print 'The file %s is already part of freesound, we re-add it again' % (sound.original_filename)
                else:
                    os.remove(sound.original_path)
                    print 'The file %s is already part of freesound, we re-add it again' % (sound.original_filename)
                    continue

            # 4 save
            sound.save()

            # 5 move to new path
            orig = os.path.splitext(os.path.basename(sound.original_filename))[0] # WATCH OUT!
            sound.base_filename_slug = "%d__%s__%s" % (sound.id, slugify(sound.user.username), slugify(orig))
            new_original_path = sound.locations("path")
            if sound.original_path != new_original_path:
                try:
                    os.makedirs(os.path.dirname(new_original_path))
                except OSError:
                    pass
                try:
                    shutil.move(sound.original_path, new_original_path)
                    #shutil.copy(sound.original_path, new_original_path)
                except IOError, e:
                    print "failed to move file from %s to %s" % (sound.original_path, new_original_path)
                    #logger.info("failed to move file from %s to %s" % (sound.original_path, new_original_path), e)
                #logger.info("moved original file from %s to %s" % (sound.original_path, new_original_path))
                sound.original_path = new_original_path
                sound.save()

            # 6 create pack if it does not exist
            if packnamef:
                if Pack.objects.filter(name=packnamef, user=u).exists():
                    p = Pack.objects.get(name=packnamef, user=u)
                else:
                    p, created = Pack.objects.get_or_create(user=u, name=packnamef)

                sound.pack = p
                #dirty_packs.append(sound.pack)

            # 7 create geotag objects
            # format: lat#lon#zoom
            if geotagf:
                lat,lon,zoom = [g for g in geotagf.split(" ") if g]
                geotag = GeoTag(user=u,
                    lat=float(lat),
                    lon=float(lon),
                    zoom=int(zoom))
                geotag.save()
                sound.geotag = geotag

            # 8 set description, tags
            sound.description = descriptionf
            sound.set_tags([t for t in tagsf.split(" ") if t])

            # 9 save!
            sound.save()

            # if(whitelisted): set moderation OK
            sound.moderation_state = 'OK'
            sound.save()

            # 10 Proces
            try:
                sound.compute_crc()
            except:
                pass

            try:
                sound.process()
            except Exception, e:
                print 'Sound with id %s could not be scheduled. (%s)' % (sound.id, str(e))

            print "Successfully uploaded sound " + sound.original_filename
