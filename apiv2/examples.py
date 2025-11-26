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
    "Search": [
        (
            "Simple search",
            [
                "apiv2/search/?query=cars",
                "apiv2/search/?query=piano&page=2",
                "apiv2/search/?query=bass -drum",
                'apiv2/search/?query="bass drum" -double',
            ],
        ),
        (
            "Search with a filter",
            [
                "apiv2/search/?query=music&filter=tag:guitar",
                "apiv2/search/?query=music&filter=type:(wav OR aiff)",
                "apiv2/search/?query=music&filter=tag:bass tag:drum",
                'apiv2/search/?query=music&filter=category:Music subcategory:"Solo instrument"',
                "apiv2/search/?query=music&filter=is_geotagged:true tag:field-recording duration:[60 TO 120]",
                "apiv2/search/?query=music&filter=samplerate:44100 type:wav channels:2",
                "apiv2/search/?query=music&filter=duration:[0.1 TO 0.3] avg_rating:[3 TO *]",
            ],
        ),
        (
            "Search with a content-based filter",
            [
                "apiv2/search/?query=piano&filter=bpm:60",
                "apiv2/search/?query=piano&filter=pitch:[435 TO 445]",
                "apiv2/search/?query=piano&filter=note_name:E",
                "apiv2/search/?query=piano&filter=note_confidence:[0.9 TO *]",
            ],
        ),
        (
            "Simple search and selection of sound fields to return in the results",
            [
                "apiv2/search/?query=alarm&fields=name,previews",
                "apiv2/search/?query=alarm&fields=name,spectral_centroid,pitch",
                "apiv2/search/?query=loop&fields=uri,onset_times",
            ],
        ),
        ("Group search results by pack", ["apiv2/search/?query=piano&group_by_pack=1"]),
        (
            "Get geotagged sounds with tag field-recording. Return only geotag and tags for each result",
            ["apiv2/search/?filter=is_geotagged:1 tag:field-recording&fields=geotag,tags"],
        ),
        (
            "Basic geospatial filtering",
            [
                'apiv2/search/?filter=geotag:"Intersects(-74.093 41.042 -69.347 44.558)"',
                'apiv2/search/?filter=geotag:"IsDisjointTo(-74.093 41.042 -69.347 44.558)"',
            ],
        ),
        (
            "Geospatial with customizable max error parameter (in degrees) and combinations of filters",
            [
                'apiv2/search/?filter=geotag:"Intersects(-74.093 41.042 -69.347 44.558) distErr=20"',
                'apiv2/search/?filter=geotag:"Intersects(-80 40 -60 50)" OR geotag:"Intersects(60 40 100 50)"&fields=id,geotag,tags',
                'apiv2/search/?filter=(geotag:"Intersects(-80 40 -60 50)" OR geotag:"Intersects(60 40 100 50)") AND tag:field-recording&fields=id,geotag,tags',
            ],
        ),
        (
            "Geospatial search for points at a maximum distance d (in km) from a latitude,longitude position and with a particular tag",
            [
                "apiv2/search/?filter={!geofilt sfield=geotag pt=41.3833,2.1833 d=10} tag:barcelona&fields=id,geotag,tags",
            ],
        ),
    ],
    "ContentSearch": [
        (
            "Setting a target as some descriptor values",
            [
                "apiv2/search/content/?target=lowlevel.pitch.mean:220",
                "apiv2/search/content/?target=lowlevel.pitch.mean:220 AND lowlevel.pitch.var:0",
            ],
        ),
        (
            "Using multidimensional descriptors in the target",
            [
                "apiv2/search/content/?target=sfx.tristimulus.mean:0,1,0&fields=id,analysis&descriptors=sfx.tristimulus.mean"
            ],
        ),
        ("Using a Freesound sound id as target", ["apiv2/search/content/?target=1234"]),
        (
            "Using an Essentia analysis file as target",
            [
                'curl -X POST -H "Authorization: Token {{your_api_key}}" -F analysis_file=@"/path/to/your_file.json" \'%s/apiv2/search/content/\''
            ],
        ),
        (
            "Using descriptors filter",
            [
                "apiv2/search/content/?descriptors_filter=lowlevel.pitch.mean:[219.9 TO 220.1]",
                "apiv2/search/content/?descriptors_filter=lowlevel.pitch.mean:[219.9 TO 220.1] AND lowlevel.pitch_salience.mean:[0.6 TO *]",
                "apiv2/search/content/?descriptors_filter=lowlevel.mfcc.mean[0]:[-1124 TO -1121]",
                "apiv2/search/content/?descriptors_filter=lowlevel.mfcc.mean[1]:[17 TO 20] AND lowlevel.mfcc.mean[4]:[0 TO 20]",
                'apiv2/search/content/?descriptors_filter=tonal.key_key:"Asharp"',
                'apiv2/search/content/?descriptors_filter=tonal.key_scale:"major"',
                'apiv2/search/content/?descriptors_filter=(tonal.key_key:"C" AND tonal.key_scale:"major") OR (tonal.key_key:"A" AND tonal.key_scale:"minor")',
                'apiv2/search/content/?descriptors_filter=tonal.key_key:"C" tonal.key_scale="major" tonal.key_strength:[0.8 TO *]',
            ],
        ),
    ],
    "CombinedSearch": [
        (
            "Combining query with target descriptors and textual filter",
            ["apiv2/search/combined/?target=rhythm.bpm:120&filter=tag:loop"],
        ),
        (
            "Combining textual query with descriptors filter",
            ["apiv2/search/combined/?filter=tag:loop&descriptors_filter=rhythm.bpm:[119 TO 121]"],
        ),
        (
            "Combining two filters (textual and descriptors)",
            ['apiv2/search/combined/?descriptors_filter=tonal.key_key:"A" tonal.key_scale:"major"&filter=tag:chord'],
        ),
        (
            "Combining textual query with multidimensional descriptors filter",
            [
                "apiv2/search/combined/?query=music&fields=id,analysis&descriptors=lowlevel.mfcc.mean&descriptors_filter=lowlevel.mfcc.mean[1]:[17 TO 20] AND lowlevel.mfcc.mean[4]:[0 TO 20]"
            ],
        ),
    ],
    # Sounds
    "SoundInstance": [
        ("Complete sound information for a particular sound (excluding descriptors)", ["apiv2/sounds/1234/"]),
        ("Getting only ID and tags", ["apiv2/sounds/1234/?fields=id,tags"]),
        ("Getting only sound name plus some descriptors", ["apiv2/sounds/1234/?fields=name,spectral_centroid,mfcc"]),
        ("Getting only some descriptors", ["apiv2/sounds/213524/?fields=mfcc,bpm"]),
    ],
    "SoundAnalysis": [
        ("Full analysis information", ["apiv2/sounds/1234/analysis/"]),
        ("Getting only tristimulus descriptor", ["apiv2/sounds/1234/analysis/?fields=tristimulus"]),
        ("Getting two or more descriptors", ["apiv2/sounds/1234/analysis/?fields=mfcc,tristimulus,warmth"]),
    ],
    "SimilarSounds": [
        (
            "Getting similar sounds",
            [
                "apiv2/sounds/80408/similar/",
                "apiv2/sounds/80408/similar/?page=2",
                "apiv2/sounds/1234/similar/?fields=name,pitch,spectral_centroid&filter=spectral_centroid:[80 TO 100] note_midi:60",
            ],
        ),
    ],
    "SoundComments": [
        ("Get sound comments", ["apiv2/sounds/14854/comments/", "apiv2/sounds/14854/comments/?page=2"]),
    ],
    "DownloadSound": [
        ("Download a sound", ["curl -H \"Authorization: Bearer {{access_token}}\" '%s/apiv2/sounds/14854/download/'"]),
    ],
    "UploadSound": [
        (
            "Upload a sound (audiofile only, no description)",
            [
                'curl -X POST -H "Authorization: Bearer {{access_token}}" -F audiofile=@"/path/to/your_file.wav" \'%s/apiv2/sounds/upload/\''
            ],
        ),
        (
            "Upload and describe a sound all at once",
            [
                'curl -X POST -H "Authorization: Bearer {{access_token}}" -F audiofile=@"/path/to/your_file.wav" -F "tags=field-recording birds nature h4n" -F "description=This sound was recorded...<br>bla bla bla..." -F "bst_category=fx-a" -F "license=Attribution" \'%s/apiv2/sounds/upload/\''
            ],
        ),
        (
            "Upload and describe a sound with name, pack and geotag",
            [
                'curl -X POST -H "Authorization: Bearer {{access_token}}" -F audiofile=@"/path/to/your_file.wav" -F "name=Another cool sound" -F "tags=field-recording birds nature h4n" -F "description=This sound was recorded...<br>bla bla bla..." -F "bst_category=fx-a" -F "license=Attribution" -F "pack=A birds pack" -F "geotag=2.145677,3.22345,14" \'%s/apiv2/sounds/upload/\''
            ],
        ),
    ],
    "PendingUploads": [
        (
            "Get uploaded sounds that are pending description, processing or moderation",
            ["curl -H \"Authorization: Bearer {{access_token}}\" '%s/apiv2/sounds/pending_uploads/'"],
        ),
    ],
    "DescribeSound": [
        (
            "Describe a sound (only with required fields)",
            [
                'curl -X POST -H "Authorization: Bearer {{access_token}}" --data "upload_filename=your_file.wav&tags=field-recording birds nature h4n&description=This sound was recorded...<br>bla bla bla...&bst_category=fx-a&license=Attribution" \'%s/apiv2/sounds/describe/\''
            ],
        ),
        (
            "Also add a name to the sound",
            [
                'curl -X POST -H "Authorization: Bearer {{access_token}}" --data "upload_filename=your_file.wav&name=A cool bird sound&tags=field-recording birds nature h4n&description=This sound was recorded...<br>bla bla bla...&bst_category=fx-a&license=Attribution" \'%s/apiv2/sounds/describe/\''
            ],
        ),
        (
            "Include geotag and pack information",
            [
                'curl -X POST -H "Authorization: Bearer {{access_token}}" --data "upload_filename=your_file.wav&name=A cool bird sound&tags=field-recording birds nature h4n&description=This sound was recorded...<br>bla bla bla...&bst_category=fx-a&license=Attribution&pack=A birds pack&geotag=2.145677,3.22345,14" \'%s/apiv2/sounds/describe/\''
            ],
        ),
    ],
    #'EditSoundDescription': [
    #    ('Setting tags of an existing sound to be "new tags for the sound" and description to "New sound description..."', ['curl -X POST -H "Authorization: Bearer {{access_token}}" --data "tags=new tags for the sound&description=New sound description..." \'%s/apiv2/sounds/1234/edit/\'']),
    # ],
    "BookmarkSound": [
        (
            "Simple bookmark",
            [
                'curl -X POST -H "Authorization: Bearer {{access_token}}" --data "name=Classic thunderstorm" \'%s/apiv2/sounds/2523/bookmark/\''
            ],
        ),
        (
            "Bookmark with category",
            [
                'curl -X POST -H "Authorization: Bearer {{access_token}}" --data "name=Nice loop&category=Nice loops" \'%s/apiv2/sounds/1234/bookmark/\''
            ],
        ),
    ],
    "RateSound": [
        (
            "Rate sounds",
            [
                'curl -X POST -H "Authorization: Bearer {{access_token}}" --data "rating=5" \'%s/apiv2/sounds/2523/rate/\'',
                'curl -X POST -H "Authorization: Bearer {{access_token}}" --data "rating=4" \'%s/apiv2/sounds/1234/rate/\'',
            ],
        ),
    ],
    "CommentSound": [
        (
            "Comment sounds",
            [
                'curl -X POST -H "Authorization: Bearer {{access_token}}" --data "comment=Cool! I understand now why this is the most downloaded sound in Freesound..." \'%s/apiv2/sounds/2523/comment/\'',
                'curl -X POST -H "Authorization: Bearer {{access_token}}" --data "comment=A very cool sound!" \'%s/apiv2/sounds/1234/comment/\'',
            ],
        ),
    ],
    # Users
    "UserInstance": [
        ("User information", ["apiv2/users/reinsamba/", "apiv2/users/Freed/"]),
    ],
    "UserSounds": [
        (
            "Getting user sounds",
            [
                "apiv2/users/Jovica/sounds/",
                "apiv2/users/Jovica/sounds/?page=2",
                "apiv2/users/Jovica/sounds/?fields=id,bitdepth,type,samplerate",
            ],
        ),
    ],
    "UserPacks": [
        ("Getting user packs", ["apiv2/users/reinsamba/packs/", "apiv2/users/reinsamba/packs/?page=2"]),
    ],
    # Packs
    "PackInstance": [
        ("Getting a pack", ["apiv2/packs/9678/"]),
    ],
    "PackSounds": [
        ("Getting pack sounds", ["apiv2/packs/9678/sounds/", "apiv2/packs/9678/sounds/?fields=id,name"]),
    ],
    "DownloadPack": [
        ("Download a pack", ["curl -H \"Authorization: Bearer {{access_token}}\" '%s/apiv2/packs/9678/download/'"]),
    ],
    # Me
    "MeBookmarkCategories": [
        (
            "Users bookmark categories",
            ["curl -H \"Authorization: Bearer {{access_token}}\" '%s/apiv2/me/bookmark_categories/'"],
        ),
    ],
    "MeBookmarkCategorySounds": [
        (
            "Getting uncategorized bookmarks",
            ["curl -H \"Authorization: Bearer {{access_token}}\" '%s/apiv2/me/bookmark_categories/0/sounds/'"],
        ),
        (
            "Getting sounds of a particular bookmark category",
            [
                "curl -H \"Authorization: Bearer {{access_token}}\" '%s/apiv2/me/bookmark_categories/11819/sounds/'",
                "curl -H \"Authorization: Bearer {{access_token}}\" '%s/apiv2/me/bookmark_categories/11819/sounds/?fields=duration,previews'",
            ],
        ),
    ],
}
