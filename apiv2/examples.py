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
        ('Search with filter', ['apiv2/search/?query=music&filter=tag:guitar']),
        ('Slect return fields', ['apiv2/search/?query=alarm&fields=name,previews']),
    ],
    'AdvancedSearch': [
        ('text', ['apiv2/...todo sound advanced search examples...']),
    ],

    # Sounds
    'SoundInstance': [
        ('text', ['apiv2/...todo sound instance examples...']),
    ],
    'SoundAnalysis': [
        ('text', ['apiv2/...todo sound analysis examples...']),
    ],
    'SimilarSounds': [
        ('text', ['apiv2/...todo similar sounds examples...']),
    ],
    'SoundComments': [
        ('text', ['apiv2/...todo sound comments examples...']),
    ],
    'DownloadSound': [
        ('text', ['apiv2/...todo download sound examples...']),
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
        ('text', ['apiv2/...todo user instance examples...']),
    ],
    'UserSounds': [
        ('text', ['apiv2/...todo user sounds examples...']),
    ],
    'UserPacks': [
        ('text', ['apiv2/...todo user packs examples...']),
    ],
    'UserBookmarkCategories': [
        ('text', ['apiv2/...todo user bookmark categories examples...']),
    ],
    'UserBookmarkCategorySounds': [
        ('text', ['apiv2/...todo user bookmark category sounds examples...']),
    ],

    # Packs
    'PackInstance': [
        ('text', ['apiv2/...todo pack instance examples...']),
    ],
    'PackSounds': [
        ('text', ['apiv2/...todo pack sounds examples...']),
    ],
    'DownloadPack': [
        ('text', ['apiv2/...todo pack download examples...']),
    ],

}