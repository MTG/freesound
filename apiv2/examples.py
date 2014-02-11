# -*- coding: utf-8 -*-

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

examples = {
    # Search
    'Search': [
        ('Simple search', ['apiv2/search/?query=cars', 'apiv2/search/?query=piano&page=2']),
        ('Search with a filter', ['apiv2/search/?query=music&filter=tag:guitar', 'apiv2/search/?query=music&filter=type:(wav OR aiff)']),
        ('Simple search and selection of sound fields to return in the results', ['apiv2/search/?query=alarm&fields=name,previews']),
        ('Get geotagged sounds with tag field-recording. Return only geotag and tags for each result', ['apiv2/search/?filter=is_geotagged:1 tag:field-recording&fields=geotag,tags']),
        ('Todo', ['apiv2/complete previous examples and add more...']),
    ],
    'AdvancedSearch': [
        ('Todo...', ['apiv2/...todo sound advanced search examples...']),
        ('Textual query plus filtering of multidiemnsional descriptors', ['apiv2/search/advanced/?query=music&fields=id,analysis&descriptors=.lowlevel.mfcc.mean&descriptors_filter=.lowlevel.mfcc.mean[1]:[17 TO 20] AND .lowlevel.mfcc.mean[4]:[0 TO 20]']),
    ],

    # Sounds
    'SoundInstance': [
        ('Complete sound information', ['apiv2/sounds/1234/']),
        ('Getting only id and tags for a particular sound', ['apiv2/sounds/1234/?fields=id,tags']),
        ('Getting sound name and spectral centroid values (second example gets normalized centroid values)', ['apiv2/sounds/1234/?fields=name,analysis&descriptors=.lowlevel.spectral_centroid', 'apiv2/sounds/1234/?fields=name,analysis&descriptors=.lowlevel.spectral_centroid&normalized=1']),
    ],
    'SoundAnalysis': [
        ('Full analysis information', ['apiv2/sounds/1234/analysis/']),
        ('Getting only tristimulus descriptor', ['apiv2/sounds/1234/analysis/?descriptors=.sfx.tristimulus']),
        ('Getting normalized mean mfcc descriptors', ['apiv2/sounds/1234/analysis/?descriptors=.lowlevel.mfcc.mean&normalized=1']),
    ],
    'SimilarSounds': [
        ('Getting similar sounds', ['apiv2/sounds/80408/similar/', 'apiv2/sounds/80408/similar/?page=2', 'apiv2/sounds/1234/similar/?fields=name,analysis&descriptors=.lowlevel.pitch.mean&descriptors_filter=.lowlevel.pitch.mean:[90 TO 110]']),
    ],
    'SoundComments': [
        ('Get sound comments', ['apiv2/sounds/14854/comments/', 'apiv2/sounds/14854/comments/?page=2']),
    ],
    'DownloadSound': [
        ('Download a sound', ['curl -X POST -H "Authorization: Bearer {{access_token}}" %s/apiv2/sounds/14854/download/']),
    ],
    'UploadSound': [
        ('Upload a sound', ['curl -H "Authorization: Bearer {{access_token}}" -F audiofile=@"/path/to/your_file.wav" %s/apiv2/sounds/upload/']),
    ],
    'NotYetDescribedUploadedSounds': [
        ('Get sounds that have not been yet described', ['curl -X POST -H "Authorization: Bearer {{access_token}}" %s/apiv2/sounds/not_yet_described/']),
    ],
    'DescribeSound': [
        ('Describe a sound (only with required fields)', ['curl -X POST -H "Authorization: Bearer {{access_token}}" --data "upload_filename=your_file.wav&tags=field-recording birds nature h4n&description=This sound was recorded...<br>bla bla bla...&license=Attribution" %s/apiv2/sounds/describe/']),
        ('Also add a name to the sound', ['curl -X POST -H "Authorization: Bearer {{access_token}}" --data "upload_filename=your_file.wav&name=A cool bird sound&tags=field-recording birds nature h4n&description=This sound was recorded...<br>bla bla bla...&license=Attribution" %s/apiv2/sounds/describe/']),
        ('Include geotag and pack information', ['curl -X POST -H "Authorization: Bearer {{access_token}}" --data "upload_filename=your_file.wav&name=A cool bird sound&tags=field-recording birds nature h4n&description=This sound was recorded...<br>bla bla bla...&license=Attribution&pack=A birds pack&geotag=2.145677,3.22345,14" %s/apiv2/sounds/describe/']),
    ],
    'UploadAndDescribeSound': [
        ('Upload and describe a sound all at once', ['curl -X POST -H "Authorization: Bearer {{access_token}}" -F audiofile=@"/path/to/your_file.wav" -F "tags=field-recording birds nature h4n" -F "description=This sound was recorded...<br>bla bla bla..." -F "license=Attribution" %s/apiv2/sounds/upload_and_describe/']),
        ('Upload and describe a sound with name, pack and geotag', ['curl -X POST -H "Authorization: Bearer {{access_token}}" -F audiofile=@"/path/to/your_file.wav" -F "name=Another cool sound" -F "tags=field-recording birds nature h4n" -F "description=This sound was recorded...<br>bla bla bla..." -F "license=Attribution" -F "pack=A birds pack" -F "geotag=2.145677,3.22345,14" %s/apiv2/sounds/upload_and_describe/']),
    ],
    'BookmarkSound': [
        ('Simple bookmark', ['curl -X POST -H "Authorization: Bearer {{access_token}}" --data "name=Classic thunderstorm" %s/apiv2/sounds/2523/bookmark/']),
        ('Bookmark with category', ['curl -X POST -H "Authorization: Bearer {{access_token}}" --data "name=Nice loop&category=Nice loops" %s/apiv2/sounds/1234/bookmark/']),
    ],
    'RateSound': [
        ('Rate sounds', ['curl -X POST -H "Authorization: Bearer {{access_token}}" --data "rating=5" %s/apiv2/sounds/2523/rate/', 'curl -X POST -H "Authorization: Bearer {{access_token}}" --data "rating=4" %s/apiv2/sounds/1234/rate/']),
    ],
    'CommentSound': [
        ('Comment sounds', ['curl -X POST -H "Authorization: Bearer {{access_token}}" --data "comment=Cool! I understand now why this is the most downloaded sound in Freesound..." %s/apiv2/sounds/2523/comment/', 'curl -X POST -H "Authorization: Bearer {{access_token}}" --data "comment=A very cool sound!" %s/apiv2/sounds/1234/comment/']),
    ],

    # Users
    'UserInstance': [
        ('User information', ['apiv2/users/reinsamba/', 'apiv2/users/Freed/']),
    ],
    'UserSounds': [
        ('Getting user sounds', ['apiv2/users/Jovica/sounds/', 'apiv2/users/Jovica/sounds/?page=2', 'apiv2/users/Jovica/sounds/?fields=id,bitdepth,type,samplerate']),
    ],
    'UserPacks': [
        ('Getting user packs', ['apiv2/users/reinsamba/packs/', 'apiv2/users/reinsamba/packs/?page=2']),
    ],
    'UserBookmarkCategories': [
        ('Users bookmark categories', ['apiv2/users/frederic.font/bookmark_categories/']),
    ],
    'UserBookmarkCategorySounds': [
        ('Getting uncategorized bookmarks', ['apiv2/users/frederic.font/bookmark_categories/0/sounds/']),
        ('Getting sounds of a particular bookmark cateogry', ['apiv2/users/frederic.font/bookmark_categories/11819/sounds/', 'apiv2/users/frederic.font/bookmark_categories/11819/sounds/?fields=duration,previews']),
    ],

    # Packs
    'PackInstance': [
        ('Getting a pack', ['apiv2/packs/9678/']),
    ],
    'PackSounds': [
        ('Getting pack sounds', ['apiv2/packs/9678/sounds/','apiv2/packs/9678/sounds/?fields=id,name']),
    ],
    'DownloadPack': [
        ('Download a pack', ['apiv2/packs/9678/download/']),
    ],

}