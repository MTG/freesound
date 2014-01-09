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
        ('Search with a filter', ['apiv2/search/?query=music&filter=tag:guitar']),
        ('Simple search and selection of sound fields to return in the results', ['apiv2/search/?query=alarm&fields=name,previews']),
    ],
    'AdvancedSearch': [
        ('text', ['apiv2/...todo sound advanced search examples...']),
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
        ('Download a sound', ['apiv2/sounds/14854/download/']),
    ],
    'UploadSound': [
        ('text', ['apiv2/...todo upload sound examples...']),
    ],
    'NotYetDescribedUploadedSounds': [
        ('text', ['apiv2/...todo not yet described... examples...']),
    ],
    'DescribeSound': [
        ('text', ['apiv2/...todo describe sound examples...']),
    ],
    'UploadAndDescribeSound': [
        ('text', ['apiv2/...todo upload and describe sound examples...']),
    ],
    'BookmarkSound': [
        ('text', ['apiv2/...todo bookmark sound examples...']),
    ],
    'RateSound': [
        ('text', ['apiv2/...todo rate sound examples...']),
    ],
    'CommentSound': [
        ('text', ['apiv2/...todo comment sound examples...']),
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