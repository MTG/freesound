.. _resources_apiv1:

APIv1 Resources
<<<<<<<<<<<<<<<

.. contents::
    :depth: 3


Sounds
>>>>>>


Sound Search resource
=====================

URI
---

::

  /sounds/search

The only allowed method is GET.

GET
---

Request
'''''''

**Parameters**

==================  ======  ========  =================================
Name                Type    Required  Description
==================  ======  ========  =================================
q                   string  no        The query!
p                   number  no        The page of the search result to get
f                   string  no	      The filter
s                   string  no	      How to sort the results
fields	            string  no	      Fields
sounds_per_page     number  no	      Number of sounds to return in each page (be aware that large numbers may produce sloooow queries, maximum allowed is 100 sounds per page)
g                   bool    no        Group results in packs. g=0 (default) don't group, g=1 group. See below.
==================  ======  ========  =================================

**q for query**

From the Solr Wiki: This is designed to be support raw input
strings provided by users with no special escaping. '+' and '-'
characters are treated as "mandatory" and "prohibited" modifiers for
the subsequent terms. Text wrapped in balanced quote characters '"'
are treated as phrases, any query containing an odd number of quote
characters is evaluated as if there were no quote characters at all.
Wildcards are not supported.

default is "+"

Some examples::

  q=bass -drum
  q="bass drum" -double
  q=username bass heavy -drum

The q-query does a weighted search over many of the the fields defined
below. So, searching for "1234" will find you files with id 1234,
files that have 1234 in the description etc etc. Think of "q" as being
the "universal google search parameter".

**f for filters**

all filters come in the form fieldname:query or fieldname:"query"
and fieldname can be any of these:

======================  ====================================================
id		        integer, sound id on freesound
username: 		string, not tokenized
created: 		date
original_filename: 	string, tokenized
description: 		string, tokenized
tag: 			string
license: 		string ("Attribution", "Attribution Noncommercial" or "Creative Commons 0")
is_remix: 		boolean
was_remixed: 		boolean
pack: 			string
pack_tokenized: 	string, tokenized
is_geotagged: 		boolean
type: 			string, original file type, one of wav,
    			aif, aiff, ogg, mp3, flac, m4a
duration: 		numerical, duration of sound in seconds
bitdepth: 		integer, WARNING is not to be trusted right now
bitrate: 		numerical, WARNING is not to be trusted right now
samplerate: 		integer
filesize: 		integer, file size in bytes
channels: 		integer, number of channels in sound,
			mostly 1 or 2, sometimes more
md5: 			string, 32-byte md5 hash of file
num_downloads: 		integer, all zero right now (not imported data)
avg_rating: 		numerical, average rating, from 0 to 5
num_ratings: 		integer, number of ratings
comment: 		string, tokenized
comments: 		numerical, number of comments
======================  ====================================================

string filters can be quoted to keep them together
(see examples) numeric/integer filters can have a
range as a query, looking like this (the "TO" needs
to be upper case!)::

  [start TO end]
  [* TO end]
  [start to \*]

dates can have ranges (and math) too (the "TO" needs to be upper case!)::

  created:[* TO NOW]
  created:[1976-03-06T23:59:59.999Z TO *]
  created:[1995-12-31T23:59:59.999Z TO 2007-03-06T00:00:00Z]
  created:[NOW-1YEAR/DAY TO NOW/DAY+1DAY]
  created:[1976-03-06T23:59:59.999Z TO 1976-03-06T23:59:59.999Z+1YEAR]
  created:[1976-03-06T23:59:59.999Z/YEAR TO 1976-03-06T23:59:59.999Z]

Some examples::

  f=tag:bass tag:drum
  f=tag:bass description:"heavy distortion"
  f=is_geotagged:true tag:field-recording duration:[60 TO 120]
  f=samplerate:44100 type:wav channels:2
  f=duration:[0.1 TO 0.3] avg_rating:[3 TO *]

**p for page**

The p parameter can be used to paginate through the results.
Every page holds 30 sounds and the first page is page 1.

**s for sort**

The s parameter determines how the results are sorted, and can only be one
of the following.

==============  ====================================================================
Option          Explanation
==============  ====================================================================
score           Sort by a relevance score returned by our search engine (default).
duration_desc   Sort by the duration of the sounds, longest sounds first.
duration_asc    Same as above, but shortest sounds first.
created_desc    Sort by the date of when the sound was added. newest sounds first.
created_asc	Same as above, but oldest sounds first.
downloads_desc  Sort by the number of downloads, most downloaded sounds first.
downloads_asc   Same as above, but least downloaded sounds first.
rating_desc     Sort by the average rating given to the sounds, highest rated first.
rating_asc      Same as above, but lowest rated sounds first.
==============  ====================================================================


.. _custom-fields:

**fields for fields**

The response of the search resource contains an array of sounds and each sound is
represented with a number of pre-defined fields (see :ref:`sound-search-response` for more information).
Sometimes we only need specific information about sounds such as their id, their tagline or
their name, but the array of sounds that is returned contains many more properties useless for us (thus we are using
a lot of badwidth that we could save).

In these cases, parameter ``fields`` allows to define the exact list of fields that we want to obtain for each sound.
Fields are specified as a list of properties (choosen from any of those listed in :ref:`sound-get-response`) separated by commas.
For example, if we perform a search and we only want to get sound ids and duration, we can use fields parameter as ``fields=id,duration``.

This parameter can be used in any resource that returns an array of sounds.


.. _grouping:

**g for grouping results**

This parameter represents a boolean option to indicate whether to collapse results belonging to sounds of the same pack into single entries
in the sounds list. With g=1, if search results contain more than one sound that belongs to the same pack,
only one sound for each distinct pack is returned (sounds with no packs are returned aswell). However, the
returned sound will feature two extra properties to access these other sounds omitted from the results list:
``n_results_from_the_same_pack``: indicates how many other results belong to the same pack (and have not been returned)
``results_from_the_same_pack``: uri pointing to the list of omitted sound results of the same pack (also including the result which has already been returned)



**Curl Examples**

::

  # Get the third page with the query 'dogs', with the most downloaded sounds first.
  curl https://freesound.org/api/sounds/search?p=3&q=dogs&s=downloads_desc
  # Get the most recent uploaded sounds with the tag 'synth' and querying for 'bass'
  curl https://freesound.org/api/sounds/search?q=bass&f=tag:synth&s=created_desc
  # Get short kick sounds
  curl https://freesound.org/api/sounds/search?q=kick&f=duration:[0.1 TO 0.3]
  # Get sound id and tags of short kick sounds
  curl https://freesound.org/api/sounds/search?q=kick&f=duration:[0.1 TO 0.3]&fields=id,tags


.. _sound-search-response:

Sound search response
'''''''''''''''''''''

**Properties**

===========  =======  ===========================================================================================
Name         Type     Description
===========  =======  ===========================================================================================
sounds       array    Array of sounds. Each sound looks like a reduced version of the :ref:`sound-get-response` (with less information).
num_results  int      Number of sounds found that match your search
num_pages    int      Number of pages (as the result is paginated)
previous     URI      The URI to go back one page in the search results.
next         URI      The URI to go forward one page in the search results.
===========  =======  ===========================================================================================



**JSON Example**

::

  {
    "num_results": 810,
    "sounds": [
      {
            "analysis_stats": "https://freesound.org/api/sounds/116841/analysis",
            "analysis_frames": "https://freesound.org/data/analysis/116/116841_854810_frames.json",
            "waveform_m": "https://freesound.org/data/displays/116/116841_854810_wave_M.png",
            "type": "wav",
            "original_filename": "falling metal 3 - 20.3.11.wav",
            "tags": [
                "voice",
                "siren",
                "metal",
                "bird",
                "industry",
                "trains",
                "police",
                "ambulance",
                "sunday",
                "dog",
                "barking",
                "ambience",
                "seagull",
                "car",
                "horn",
                "shouting"
            ],
            "url": "https://freesound.org/people/toiletrolltube/sounds/116841/",
            "preview-hq-ogg": "https://freesound.org/data/previews/116/116841_854810-hq.ogg",
            "serve": "https://freesound.org/api/sounds/116841/serve",
            "similarity": "https://freesound.org/api/sounds/116841/similar",
            "preview-lq-ogg": "https://freesound.org/data/previews/116/116841_854810-lq.ogg",
            "spectral_m": "https://freesound.org/data/displays/116/116841_854810_spec_M.jpg",
            "preview-lq-mp3": "https://freesound.org/data/previews/116/116841_854810-lq.mp3",
            "user": {
                "username": "toiletrolltube",
                "url": "https://freesound.org/people/toiletrolltube/",
                "ref": "https://freesound.org/api/people/toiletrolltube"
            },
            "spectral_l": "https://freesound.org/data/displays/116/116841_854810_spec_L.jpg",
            "duration": 5.6986699999999999,
            "waveform_l": "https://freesound.org/data/displays/116/116841_854810_wave_L.png",
            "ref": "https://freesound.org/api/sounds/116841",
            "id": 116841,
            "preview-hq-mp3": "https://freesound.org/data/previews/116/116841_854810-hq.mp3",
            "pack": "https://freesound.org/api/packs/7333"
        },
        [...more sounds...]
        {
            "analysis_stats": "https://freesound.org/api/sounds/113785/analysis",
            "analysis_frames": "https://freesound.org/data/analysis/113/113785_1956076_frames.json",
            "waveform_m": "https://freesound.org/data/displays/113/113785_1956076_wave_M.png",
            "type": "wav",
            "original_filename": "Woof Woof Drum.wav",
            "tags": [
                "drum",
                "bass",
                "dog",
                "woof",
                "bark",
                "canvas",
                "hit"
            ],
            "url": "https://freesound.org/people/Puniho/sounds/113785/",
            "preview-hq-ogg": "https://freesound.org/data/previews/113/113785_1956076-hq.ogg",
            "serve": "https://freesound.org/api/sounds/113785/serve",
            "similarity": "https://freesound.org/api/sounds/113785/similar",
            "preview-hq-mp3": "https://freesound.org/data/previews/113/113785_1956076-hq.mp3",
            "spectral_m": "https://freesound.org/data/displays/113/113785_1956076_spec_M.jpg",
            "preview-lq-mp3": "https://freesound.org/data/previews/113/113785_1956076-lq.mp3",
            "user": {
                "username": "Puniho",
                "url": "https://freesound.org/people/Puniho/",
                "ref": "https://freesound.org/api/people/Puniho"
            },
            "spectral_l": "https://freesound.org/data/displays/113/113785_1956076_spec_L.jpg",
            "duration": 2.6059399999999999,
            "waveform_l": "https://freesound.org/data/displays/113/113785_1956076_wave_L.png",
            "ref": "https://freesound.org/api/sounds/113785",
            "id": 113785,
            "preview-lq-ogg": "https://freesound.org/data/previews/113/113785_1956076-lq.ogg"
        }
    ],
    "previous": "https://freesound.org/api/sounds/search?q=dogs&p=1&f=&s=downloads_desc",
    "num_pages": 27,
    "next": "https://freesound.org/api/sounds/search?q=dogs&p=3&f=&s=downloads_desc"
  }


Sound Content-based Search resource
===================================

Content-based search can be used as an alternative way for querying the freesound database. With content-based search you can
perform queries such as "give me all the sounds whose pitch is between 218 and 222 Hz", or "all the sounds whose key is A#", or
"20 sounds that are closer to having a spectral centroid of 200hz and a pitch of 180hz"... Here (:ref:`content-search-descriptors`) you can check
which descriptors can be used in the content based search.

Generally there are two ways to specify a query for content based search. One is defining a *target* and the other a *filter*. They can also be combined.
By defining *target* you specify a number of descriptor names and their desired values, and the api returns a list of sounds that closely matches the desired descriptor values.
Sounds are sorted by similarity, thus the first sound of the returned list will be the one whose indicated descriptor values are closer to the values indicated in the target.
When using a *filter*, only the sounds that comply with the filter constraints are returned. Filter constraints can be defined as ranges for particular descriptors (ex: pitch between X and Y) or exact values for certain properties (ex: pitch equal to 220 or key equal to A#).


URI
---

::

  /sounds/content_search

The only allowed method is GET.

GET
---

Request
'''''''


**Parameters**

==================  ======  ========  =================================
Name                Type    Required  Description
==================  ======  ========  =================================
t                   string  no        Target
f                   string  no	      Filter
p                   number  no	      Page number (same as in search resource)
fields	            string  no	      Fields (same as in search resource)
sounds_per_page     number  no	      Number of sounds to return in each page (be aware that large numbers may produce sloooow queries, maximum allowed is 100 sounds per page)
max_results         number  no        The maximum number of results to get in each query (default = 15)
==================  ======  ========  =================================

**t for target**

A target is defined as a series of descriptors and their values. Descriptors used as targets **can only be** either numerical or vectors, but not any "stringed" descriptor such as *.tonal.key_key*.
Several descriptors can be defined in the target concatenating them with blank spaces. Here are some examples::

  t=.lowlevel.pitch.mean:220
  t=.lowlevel.pitch.mean:220 .lowlevel.pitch_salience.mean:1.0
  t=.sfx.tristimulus.mean:0.8,0.3,0.0

Notice that when using a target without a filter, the api will ALLWAYS return sounds (even if they are really distant).
Actually, content-based search using a target and no filter can be considered as a way of similarity search by manually specifying the descriptors to use. The whole database is *sorted* according to the specified target.


**f for filter**

Filters are defined with a similar syntax as in the normal query filters. In this case, also non numerical descriptors can be used.
Content-based search filters also allow AND/OR operators and pharentheses to specify complex conditions.

To only return sounds that have a particular descriptor value it must be indicated as::

  descriptor_name:value

Notice that defining an exact value for a filter is only recommended for non numerical descriptors, as for numerical ones it might be hard to find an EXACT match (it is better to define a very small range).
String descriptors must be sorrounded by double quotes ("). Note that character # must be replaced by the string "sharp" as in urls # character has another meaning (see the example).

To indicate filter ranges the syntax is the same as in the normal search::

  [start TO end]
  [* TO end]
  [start TO *]

Here you have some examples of defining filters::

  f=.tonal.key_key:"Asharp"
  f=.lowlevel.spectral_centroid.mean:[500 TO *]
  f=.lowlevel.pitch.mean:[219 TO 221]
  f=(.tonal.key_key:"C" AND .tonal.key_scale:"major") OR (.tonal.key_key:"A" AND .tonal.key_scale:"minor")
  f=.tonal.key_key:"C" .tonal.key_scale="major" .tonal.key_strength:[0.8 TO *]




**Curl Examples**

::

  curl https://freesound.org/api/sounds/content_search?t=.sfx.tristimulus.mean:0.8,0.3,0.0
  curl https://freesound.org/api/sounds/content_search?f=.tonal.key_key:"Asharp"
  curl https://freesound.org/api/sounds/content_search?f=(.tonal.key_key:"C" AND .tonal.key_scale:"major") OR (.tonal.key_key:"A" AND .tonal.key_scale:"minor")&t=.tonal.key_strength:1.0&max_results:5



Sound content-based search response
'''''''''''''''''''''''''''''''''''
The response is the same as the :ref:`sound-search-response`. Sounds are sorted by similarity to the gived target (if given). If no target is specified, sounds are sorted by id (ascendent order).



Sound resource
==============

URI
---

::

  /sounds/<sound_id>

The only allowed method is GET.

GET
---

A GET request to the sound resource returns all the information about the sound.

Request
'''''''

**Curl Example**

::

  curl https://freesound.org/api/sounds/83295

.. _sound-get-response:

Sound response
''''''''''''''

**Properties**

====================  ================  ====================================================================================
Name                  Type              Description
====================  ================  ====================================================================================
id                    number            The sound's unique identifier.
ref                   URI               The URI for this sound.
url                   URI               The URI for this sound on the Freesound website.
preview-hq-mp3        URI               The URI for retrieving a high quality (~128kbps) mp3 preview of the sound.
preview-lq-mp3        URI               The URI for retrieving a low quality (~64kbps) mp3 preview of the sound.
preview-hq-ogg        URI               The URI for retrieving a high quality (~192kbps) ogg preview of the sound.
preview-lq-ogg        URI               The URI for retrieving a low quality (~80kbps) ogg of the sound.
serve                 URI               The URI for retrieving the original sound.
similarity            URI               URI pointing to the similarity resource (to get a list of similar sounds).
type                  string            The type of sound (wav, aif, aiff, mp3, etc.).
duration              number            The duration of the sound in seconds.
samplerate            number            The samplerate of the sound.
bitdepth              number            The bit depth of the sound.
filesize              number            The size of the file in bytes.
bitrate               number            The bit rate of the sound in kbps.
channels              number            The number of channels.
original_filename     string            The name of the sound file when it was uploaded.
description           string            The description the user gave the sound.
tags                  array[strings]    An array of tags the user gave the sound.
license               string            The license under which the sound is available to you.
created               string            The date of when the sound was uploaded.
num_comments          number            The number of comments.
num_downloads         number            The number of times the sound was downloaded.
num_ratings           number            The number of times the sound was rated.
avg_rating            number            The average rating of the sound.
pack                  URI               If the sound is part of a pack, this URI points to that pack's API resource.
geotag                object            A dictionary with the latitude ('lat') and longitude ('lon') of the geotag (only for sounds that have been geotagged).
user                  object            A dictionary with the username, url, and ref for the user that uploaded the sound.
spectral_m            URI               A visualization of the sounds spectrum over time, jpeg file (medium).
spectral_l            URI               A visualization of the sounds spectrum over time, jpeg file (large).
waveform_m            URI               A visualization of the sounds waveform, png file (medium).
waveform_l            URI               A visualization of the sounds waveform, png file (large).
analysis              URI               URI pointing to the analysis results of the sound (see :ref:`analysis-docs`).
analysis_frames       URI               The URI for retrieving a JSON file with analysis information for each frame of the sound (see :ref:`analysis-docs`).
====================  ================  ====================================================================================

**JSON Example**

::

  {
    "num_ratings": 0,
    "duration": 260.98849999999999,
    "samplerate": 44000.0,
    "preview-hq-ogg": "https://freesound.org/data/previews/17/17185_18799-hq.ogg",
    "id": 17185,
    "preview-lq-ogg": "https://freesound.org/data/previews/17/17185_18799-lq.ogg",
    "bitdepth": 16,
    "num_comments": 0,
    "filesize": 45934020,
    "preview-hq-mp3": "https://freesound.org/data/previews/17/17185_18799-hq.mp3",
    "type": "wav",
    "analysis_stats": "https://freesound.org/api/sounds/17185/analysis",
    "description": "The most beautiful nightingale recording I've ever made. Forest near Cologne, Germany,June 2004, Vivanco EM35 with preamp into Sony DAT-recorder.",
    "tags": [
        "bulbul",
        "fulemule",
        "csalogany",
        "luscinia-megarhynchos",
        "etelansatakieli",
        "sornattergal",
        "sydnaktergal",
        "ruisenor-comun",
        "rossignol-philomele",
        "nachtigall",
        "sydlig-nattergal",
        "slowik-rdzawy",
        "rouxinol",
        "usignolo",
        "nachtegaal",
        "rossinyol",
        "rossignol",
        "spring",
        "nightingale",
        "forest",
        "bird",
        "birdsong",
        "nature",
        "field-recording"
    ],
    "serve": "https://freesound.org/api/sounds/17185/serve",
    "similarity": "https://freesound.org/api/sounds/17185/similar",
    "spectral_m": "https://freesound.org/data/displays/17/17185_18799_spec_M.jpg",
    "spectral_l": "https://freesound.org/data/displays/17/17185_18799_spec_L.jpg",
    "user": {
        "username": "reinsamba",
        "url": "https://freesound.org/people/reinsamba/",
        "ref": "https://freesound.org/api/people/reinsamba"
    },
    "bitrate": 1408,
    "num_downloads": 0,
    "analysis_frames": "https://freesound.org/data/analysis/17/17185_18799_frames.json",
    "channels": 2,
    "license": "http://creativecommons.org/licenses/sampling+/1.0/",
    "created": "2006-03-19 23:53:37",
    "url": "https://freesound.org/people/reinsamba/sounds/17185/",
    "ref": "https://freesound.org/api/sounds/17185",
    "avg_rating": 0.0,
    "preview-lq-mp3": "https://freesound.org/data/previews/17/17185_18799-lq.mp3",
    "original_filename": "Nightingale song 3.wav",
    "waveform_l": "https://freesound.org/data/displays/17/17185_18799_wave_L.png",
    "waveform_m": "https://freesound.org/data/displays/17/17185_18799_wave_M.png",
    "pack": "https://freesound.org/api/packs/455"
  }

Sound Geotags resource
======================

URI
---

::

  /sounds/geotag/

The only allowed method is GET.

GET
---

A GET request to the sound resource returns a list of sounds that have been geotagged inside a space defined with url parameters.

Request
'''''''

**Parameters**

==================  ======  ========  =================================
Name                Type    Required  Description
==================  ======  ========  =================================
min_lat	            number  no        Minimum latitude [-90 to 90]
max_lat             number  no        Maximum latitude [-90 to 90]
min_lon             number  no	      Minimum longitude [-180 to 180]
max_lon	            number  no	      Maximum longitude [-180 to 180]
p                   number  no        The page of the search result to get
fields	            string  no	      Fields
sounds_per_page     number  no	      Number of sounds to return in each page (be aware that large numbers may produce sloooow queries, maximum allowed is 100 sounds per page)
==================  ======  ========  =================================

**latitude and longitude parameters**

Geotags are represented as points defined by a latitude and a longitude parameters. Displying a world map as a rectangle, latitude is the x axis and ranges from -90 to 90, while longitude is the y axis and ranges from -180 to 180.

"Sound Geotags resource" allows to define a rectangular space inside the "world map" rectangle and returns a list of all the sounds that have been geotagged inside the defined space.

This rectangular space is specified with ``min_lat``, ``min_lon`` url parameters for the bottom-left corner and ``max_lat``, ``max_lon`` for the top-right corner. The following image shows an example.

    .. image:: _static/geotags/geotag_normal.png
        :height: 300px

The definition of the rectangle assumes that world map is a continuous space where latitude 90 = -90 and longitude 180 = -180. Thus, rectangles can wrap the edges of the map. This is achieved by using ``min_lat`` greater than ``max_lat`` or ``max_lon`` smaller than ``min_lon``.
The following images show examples of these cases. If ``min_lon`` > ``max_lon``:

    .. image:: _static/geotags/geotag_lon_changed.png
        :height: 300px

Example for ``min_lat`` > ``max_lat``:

    .. image:: _static/geotags/geotag_lat_changed.png
        :height: 300px

Finally, an example for ``min_lat`` > ``max_lat`` and ``min_lon`` > ``max_lon``:

    .. image:: _static/geotags/geotag_both_changed.png
        :height: 300px



**Curl Example**

::

  curl https://freesound.org/api/sounds/geotag/?min_lon=2.005176544189453&max_lon=2.334766387939453&min_lat=41.3265528618605&max_lat=41.4504467428547


Response
''''''''
A paginated sound list like in the :ref:`sound-search-response` with the addition of a ``geotag`` property which indicates the latitude (``lat``) and longitude (``lon``) values for each sound.

Sound Analysis resource
=======================

When a file is uploaded in Freesound it is automatically analyzed. Several descriptors are
extracted and the results can be retrieved through this URI. The analysis is
done by the audio analysis tool Essentia, property of the MTG_ and
exclusively licensed to BMAT_. For detailed documentation on all the
descriptors see :ref:`analysis-docs`.

.. _MTG: http://mtg.upf.edu/
.. _BMAT: http://www.bmat.com/


URI
---

::

  /sounds/<sound_id>/analysis/<filter>

The only allowed method is GET.

The URI variable <file_key> should be replaced by a file's key. With the
<filter> variable you can select and retrieve a part of the analysis data.
When no <filter> is included the complete analysis data is returned.

The analysis data is organized in a tree. With the filter you can traverse the
tree and select a subset of it. With the ``lowlevel`` filter, you will
retrieve all the lowlevel descriptors, and with the ``lowlevel/mfcc/mean``
filter you will retrieve just an array of all twelve coefficients of the
MFCC analysis. Have a look at the complete analysis data and it'll become
apparent how filtering works.

Although many descriptors are extracted using Essentia and they are all accessible through the API,
by default we only return a list of recommended descriptors which are the following ones (check analysis
documentation for details on the meaning of the descriptors and to see the complete list of available descriptors):
``audio_properties`` (length, bitrate, samplerate...), ``culture`` (western, non western), ``gender`` (male, female), ``moods`` (happy, sad...),
``timbre`` (bright, dark), ``voice_instrumental`` (whether if sound contains voice or instruments), ``acoustic`` (acoustic, not acoustic),
``electronic`` (electronic, not electronic), ``key_key``, ``key_scale``, ``key_strength`` (tonality), ``tuning_frequency``, ``bpm``, ``loudness``, ``dissonance``,
``pitch``, ``pitch_salience``, ``spectral_centroid`` (brightness) and ``mfcc`` (timbre coefficients).

GET
---

Retrieve the analysis data for a file.

Request
'''''''

**Parameters**

=========  ======  ========  ===================================================
Name       Type    Required  Description
=========  ======  ========  ===================================================
all        bool    no        If set to true, all the available analysis data
                             will be returned. This might include unstable or
                             unreliable data. For stable descriptors use the
                             recommended ones. (default=False)
                             When retrieving non recommended features, all must be set to True.
=========  ======  ========  ===================================================

**Curl Examples**

::

  # For the complete analysis result
  curl https://freesound.org/sounds/999/analysis
  # For a filtered analysis result, in this case the analyzed average loudness
  curl https://freesound.org/api/sounds/999/analysis/lowlevel/average_loudness/
  # Or for all the tonal data
  curl https://freesound.org/api/sounds/999/analysis/tonal
  # Or for all the pitch of a sound
  curl https://freesound.org/api/sounds/999/lowlevel/pitch/mean

Response
''''''''

The response consists of a JSON object. Some filters will return a JSON array.
If you use a filter that doesn't match any analysis data you will bet a
response with status code '400 Bad Request'.

If the analysis data is not available yet a 409 error message
is returned. When the analysis failed or isn't available for some other reason
a 404 message is returned.


Analysis information at the audio frame level
'''''''''''''''''''''''''''''''''''''''''''''

The analysis data described above is a summary of the analysis of all the frames
where each frame is usually 2048 samples long. Apart from this summary the analysis
results for each frame can be retrieved as well. This data can not be filtered and
will be served to you as one big JSON file. The data will also include the
configuration that was used, such as frame and hopsize. The URI to retrieve this file
is given by the ``analysis_frames`` property of a sound resource. As an example:

::

  https://freesound.org/data/analysis/17/17185_18799_frames.json



Sound Similarity resource
=========================

URI
---

::

  /sounds/<sound_id>/similar

The only allowed method is GET.

GET
---

This resource returns a list of similar sounds according to a given sound example (which is also returned as the first of the list).
``preset`` parameter can be set to indicate which kind of similarity measure must be used when computing the distance (for the moment only ``lowlevel`` is available.).

Request
'''''''

**Parameters**

==================  ======  ========  ===================================================
Name                Type    Required  Description
==================  ======  ========  ===================================================
num_results         number  no        The number of similar sounds to return (max = 100, default = 15)
preset              string  no        The similarity measure to use when retrieving similar sounds (for the moment, only ``lowlevel`` is available at is selected by default)
fields	            string  no	      Fields
sounds_per_page     number  no	      Number of sounds to return in each page (be aware that large numbers may produce sloooow queries, maximum allowed is 100 sounds per page)
==================  ======  ========  ===================================================

**Curl Examples**

::

  # Get the most similar sound to sound with id 120597 (num_results equals 2 because original sound is also returned in the list)
  curl https://freesound.org/api/sounds/120597/similar?num_results=2
  # Get the 15 most similar sounds to sound with id 11
  curl https://freesound.org/api/sounds/11/similar

Response
''''''''

The response is the same as the :ref:`sound-search-response` but with the addition of a ``distance`` property (for each sound) resembling a numerical value of "dissimilarity" respect to the query sound (then, the first sound of the result will always have distance = 0.0).
If the response is an empty list (0 results), this is because the query sound has been recently uploaded and it has not still been indexed in the similarity database.


**JSON Example**

::

  {
    "sounds": [
        {
            "analysis_stats": "https://freesound.org/api/sounds/11/analysis",
            "preview-lq-ogg": "https://freesound.org/data/previews/0/11_2-lq.ogg",
            "tags": [
                "generated",
                "sinusoid",
                "sweep",
                "clean"
            ],
            "url": "https://freesound.org/people/Bram/sounds/11/",
            "ref": "https://freesound.org/api/sounds/11",
            "id": 11,
            "preview-lq-mp3": "https://freesound.org/data/previews/0/11_2-lq.mp3",
            "serve": "https://freesound.org/api/sounds/11/serve",
            "similarity": "https://freesound.org/api/sounds/11/similar",
            "pack": "https://freesound.org/api/packs/2",
            "distance": 0.0,
            "spectral_m": "https://freesound.org/data/displays/0/11_2_spec_M.jpg",
            "spectral_l": "https://freesound.org/data/displays/0/11_2_spec_L.jpg",
            "user": {
                "username": "Bram",
                "url": "https://freesound.org/people/Bram/",
                "ref": "https://freesound.org/api/people/Bram"
            },
            "original_filename": "sweep_log.wav",
            "type": "wav",
            "duration": 2.0,
            "analysis_frames": "https://freesound.org/data/analysis/0/11_2_frames.json",
            "waveform_l": "https://freesound.org/data/displays/0/11_2_wave_L.png",
            "waveform_m": "https://freesound.org/data/displays/0/11_2_wave_M.png",
            "preview-hq-ogg": "https://freesound.org/data/previews/0/11_2-hq.ogg",
            "preview-hq-mp3": "https://freesound.org/data/previews/0/11_2-hq.mp3"
        },
        {
            "analysis_stats": "https://freesound.org/api/sounds/104551/analysis",
            "preview-lq-ogg": "https://freesound.org/data/previews/104/104551_420640-lq.ogg",
            "tags": [
                "attack",
                "air",
                "falling",
                "war",
                "drop",
                "bomb",
                "whistle"
            ],
            "url": "https://freesound.org/people/club%20sound/sounds/104551/",
            "ref": "https://freesound.org/api/sounds/104551",
            "id": 104551,
            "preview-lq-mp3": "https://freesound.org/data/previews/104/104551_420640-lq.mp3",
            "serve": "https://freesound.org/api/sounds/104551/serve",
            "similarity": "https://freesound.org/api/sounds/104551/similar",
            "pack": "https://freesound.org/api/packs/6609",
            "distance": 7122293096448.0,
            "spectral_m": "https://freesound.org/data/displays/104/104551_420640_spec_M.jpg",
            "spectral_l": "https://freesound.org/data/displays/104/104551_420640_spec_L.jpg",
            "user": {
                "username": "club sound",
                "url": "https://freesound.org/people/club%20sound/",
                "ref": "https://freesound.org/api/people/club%20sound"
            },
            "original_filename": "Bomb Whistle long.wav",
            "type": "wav",
            "duration": 30.036799999999999,
            "analysis_frames": "https://freesound.org/data/analysis/104/104551_420640_frames.json",
            "waveform_l": "https://freesound.org/data/displays/104/104551_420640_wave_L.png",
            "waveform_m": "https://freesound.org/data/displays/104/104551_420640_wave_M.png",
            "preview-hq-ogg": "https://freesound.org/data/previews/104/104551_420640-hq.ogg",
            "preview-hq-mp3": "https://freesound.org/data/previews/104/104551_420640-hq.mp3"
        },
        {
            "analysis_stats": "https://freesound.org/api/sounds/17052/analysis",
            "preview-lq-ogg": "https://freesound.org/data/previews/17/17052_4942-lq.ogg",
            "tags": [
                "sweep",
                "electronic",
                "sound",
                "supercollider"
            ],
            "url": "https://freesound.org/people/schluppipuppie/sounds/17052/",
            "ref": "https://freesound.org/api/sounds/17052",
            "id": 17052,
            "preview-lq-mp3": "https://freesound.org/data/previews/17/17052_4942-lq.mp3",
            "serve": "https://freesound.org/api/sounds/17052/serve",
            "similarity": "https://freesound.org/api/sounds/17052/similar",
            "pack": "https://freesound.org/api/packs/954",
            "distance": 161591534288896.0,
            "spectral_m": "https://freesound.org/data/displays/17/17052_4942_spec_M.jpg",
            "spectral_l": "https://freesound.org/data/displays/17/17052_4942_spec_L.jpg",
            "user": {
                "username": "schluppipuppie",
                "url": "https://freesound.org/people/schluppipuppie/",
                "ref": "https://freesound.org/api/people/schluppipuppie"
            },
            "original_filename": "sweep03_careful.aif",
            "type": "aif",
            "duration": 40.106299999999997,
            "analysis_frames": "https://freesound.org/data/analysis/17/17052_4942_frames.json",
            "waveform_l": "https://freesound.org/data/displays/17/17052_4942_wave_L.png",
            "waveform_m": "https://freesound.org/data/displays/17/17052_4942_wave_M.png",
            "preview-hq-ogg": "https://freesound.org/data/previews/17/17052_4942-hq.ogg",
            "preview-hq-mp3": "https://freesound.org/data/previews/17/17052_4942-hq.mp3"
        },
        {
            "analysis_stats": "https://freesound.org/api/sounds/93063/analysis",
            "preview-lq-ogg": "https://freesound.org/data/previews/93/93063_926020-lq.ogg",
            "tags": [
                "impulse"
            ],
            "url": "https://freesound.org/people/simonbshelley/sounds/93063/",
            "ref": "https://freesound.org/api/sounds/93063",
            "id": 93063,
            "preview-lq-mp3": "https://freesound.org/data/previews/93/93063_926020-lq.mp3",
            "serve": "https://freesound.org/api/sounds/93063/serve",
            "similarity": "https://freesound.org/api/sounds/93063/similar",
            "distance": 350841315786752.0,
            "spectral_m": "https://freesound.org/data/displays/93/93063_926020_spec_M.jpg",
            "spectral_l": "https://freesound.org/data/displays/93/93063_926020_spec_L.jpg",
            "user": {
                "username": "simonbshelley",
                "url": "https://freesound.org/people/simonbshelley/",
                "ref": "https://freesound.org/api/people/simonbshelley"
            },
            "original_filename": "sound source.wav",
            "type": "wav",
            "duration": 25.0,
            "analysis_frames": "https://freesound.org/data/analysis/93/93063_926020_frames.json",
            "waveform_l": "https://freesound.org/data/displays/93/93063_926020_wave_L.png",
            "waveform_m": "https://freesound.org/data/displays/93/93063_926020_wave_M.png",
            "preview-hq-ogg": "https://freesound.org/data/previews/93/93063_926020-hq.ogg",
            "preview-hq-mp3": "https://freesound.org/data/previews/93/93063_926020-hq.mp3"
        }
    ],
    "num_results": 4
  }

Users
>>>>>



User resource
=============

URI
---

::

  /people/<username>

The only allowed method is GET.

GET
---

A GET request to the user resource returns all the information about the user.

Request
'''''''

**Curl Examples**

::

  curl https://freesound.org/api/people/Jovica
  curl https://freesound.org/api/people/klankschap


Response
''''''''

**Properties**

====================  =======  ========================================================
Name                  Type     Description
====================  =======  ========================================================
username	      string   The user's username.
ref		      URI      The URI for this resource.
url		      URI      The profile page for the user on the Freesound website.
sounds		      URI      The API URI for this user's sound collection.
packs		      URI      The API URI for this user's pack collection.
about		      string   A small text the user wrote about himself.
home_page	      URI      The user's homepage, possibly empty.
signature	      string   The user's signature, possibly empty.
date_joined	      string   The date the user joined Freesound.
====================  =======  ========================================================


**JSON Example**

::

  {
    "username": "Jovica",
    "packs": "https://freesound.org/api/people/Jovica/packs",
    "url": "https://freesound.org/people/Jovica/",
    "about": "Policy of use: you must state somewhere somehow (credit lines, web page, whatever) that the Freesound Project served this sounds. It is irrelevant to me whether you mention or not my authorship. Can't credit? Send me a personal message. (Thanks to dobroide for these words!)\r\n\r\nIf possible, I would also like to hear where the sounds are used, so if you can send me a link or something else, please do so. Thanks!\r\n\r\nCurrently adding LAYERS & DISTOPIA sample packs!\r\n\r\nFor some more information about me, click on the links below:\r\n<a href=\"http://www.myspace.com/jovicastorer\" rel=\"nofollow\">http://www.myspace.com/jovicastorer</a>\r\n\r\nAnd this is an experimental droney label for which I do some producing, engineering, mixing and mastering:\r\n<a href=\"http://www.plaguerecordings.com/index.htm\" rel=\"nofollow\">http://www.plaguerecordings.com/index.htm</a>\r\n\r\nCurrently me and a good friend of mine are working on a new <strong>c-o-l-o-u-r-s</strong> website. \r\n\r\nThe first release, <strong>'gekarameliseerd'</strong> by <strong>Jovica Storer</strong>, is available on:\r\n- emusic: <a href=\"http://www.emusic.com/album/Jovica-Storer-Gekarameliseerd-MP3-Download/11666781.html\" rel=\"nofollow\">http://www.emusic.com/album/Jovica-Storer-Gekarameliseerd-MP3-Download/11666781.html</a>\r\n- iTunes: <a href=\"http://itunes.apple.com/WebObjects/MZStore.woa/wa/viewAlbum?i=333466000&id;=333464878&s;=143443&uo;=6\" rel=\"nofollow\">http://itunes.apple.com/WebObjects/MZStore.woa/wa/viewAlbum?i=333466000&id;=333464878&s;=143443&uo;=6</a>\r\n- Napster: <a href=\"http://free.napster.com/view/album/index.html?id=13373722\" rel=\"nofollow\">http://free.napster.com/view/album/index.html?id=13373722</a>\r\nPlease check it out and if you want to support me, buy some tracks. Many thanks! \r\n\r\nNamaste!\r\nJovica Storer",
    "home_page": "http://www.ampcast.com/music/25765/artist.php",
    "signature": "Namaste!\r\nJovica Storer\r\n<a href=\"http://www.c-o-l-o-u-r-s.com\" rel=\"nofollow\">http://www.c-o-l-o-u-r-s.com</a>",
    "sounds": "https://freesound.org/api/people/Jovica/sounds",
    "ref": "https://freesound.org/api/people/Jovica",
    "date_joined": "2005-05-07 17:49:39"
  }







User Sounds collection
======================

URI
---

::

  /people/<username>/sounds

The only allowed method is GET.

GET
---

This resource returns the collection of sounds uploaded by the user.

Request
'''''''

**Parameters**

==================  ======  ========  ========================================
Name                Type    Required  Description
==================  ======  ========  ========================================
p                   number  no        The page of the sound collection to get.
fields	            string  no	      Fields
sounds_per_page     number  no	      Number of sounds to return in each page (be aware that large numbers may produce sloooow queries, maximum allowed is 100 sounds per page)
==================  ======  ========  ========================================

**Curl Examples**

::

  curl https://freesound.org/api/people/thanvannispen/sounds
  curl https://freesound.org/api/people/inchadney/sounds?p=5

Response
''''''''

The response is the same as the :ref:`sound-search-response`.






User Packs collection
=====================

URI
---

::

  /people/<username>/packs

The only allowed method is GET.

GET
---

Retrieve an array of the user's sound packs.

Request
'''''''

**Curl Examples**

::

  curl https://freesound.org/api/people/dobroide/packs

Response
''''''''

**Properties**

The response is an array. Each item in the array follows a reduced version of the :ref:`pack-get-response`.


**JSON Example**

::

  {
    "num_results": 47,
    "packs": [
        {
            "created": "2009-09-28 09:50:08",
            "url": "https://freesound.org/people/dobroide/packs/5266/",
            "sounds": "https://freesound.org/api/packs/5266/sounds",
            "num_downloads": 0,
            "ref": "https://freesound.org/api/packs/5266",
            "name": "scrub"
        },
        {
            "created": "2009-09-20 10:55:32",
            "url": "https://freesound.org/people/dobroide/packs/5230/",
            "sounds": "https://freesound.org/api/packs/5230/sounds",
            "num_downloads": 0,
            "ref": "https://freesound.org/api/packs/5230",
            "name": "granada"
        }
    ]
  }


User Bookmark categories
========================

URI
---

::

  /people/<username>/bookmark_categories

The only allowed method is GET.

GET
---

Retrieve an array of the user's bookmark categories.

Request
'''''''

**Curl Examples**

::

  curl https://freesound.org/api/people/but2/bookmark_categories

Response
''''''''

**Properties**

The response is a dictionary. The array has two keys: 'categories' (which returns an array of categories whhere each is a dictionary with 'name', 'url' and 'sounds' properties) and 'num_results' indicating the total number of categories.

===========  ======  ===================================================
Name         Type    Description
===========  ======  ===================================================
name         String  Name of the category
url          URI     Url to the page of the category
sounds	     URI     The API URI for getting a list of the sounds bookmarked under the category
===========  ======  ===================================================

If user has some bookmarks that have not been assigned to any category, an 'Uncategorized bookmarks' category
will automatically be added to the array that will contain all these bookmarks/sounds.


User Bookmark category sound collection
=======================================

URI
---

::

  /people/<username>/bookmark_categories/[<category_id>|uncategorized]/sounds/

The only allowed method is GET.

GET
---

A paginated collection of all sounds bookmarked under a particular bookmark category (or all uncategorized bookmarks by a user).

Request
'''''''

**Parameters**

==================  ======  ========  ====================================
Name                Type    Required  Description
==================  ======  ========  ====================================
p                   number  no        The page of sounds to get
fields	            string  no	      Fields
sounds_per_page     number  no	      Number of sounds to return in each page (be aware that large numbers may produce sloooow queries, maximum allowed is 100 sounds per page)
==================  ======  ========  ====================================

**Curl Examples**

::

  curl https://freesound.org/api/people/but2/bookmark_categories/32/sounds/

Response
''''''''

The response is the same as the :ref:`sound-search-response`, with the addition of an extra field called "bookmark_name"
which shows the name the user has given to the bookmark (by default this name is the same as "original_filename", but
users can change that while adding a new bookmark).



Packs
>>>>>


Pack resource
=============

URI
---

::

  /packs/<pack_id>

The only allowed method is GET.

GET
---

Request
'''''''

**Curl Examples**

::

  curl https://freesound.org/api/packs/5107

.. _pack-get-response:

Pack response
'''''''''''''

**Properties**

====================  =======  ========================================================
Name                  Type     Description
====================  =======  ========================================================
ref		      URI      The URI for this resource.
url		      URI      The URL for this pack's page on the Freesound website.
sounds		      URI      The API URI for the pack's sound collection.
user		      object   A JSON object with the user's username, url, and ref.
name		      string   The pack's name.
description	      string      The pack's textual description (if it has any).
created		      string   The date when the pack was created.
num_downloads	      number   The number of times the pack was downloaded.
====================  =======  ========================================================

**JSON Example**

::

  {
    "created": "2009-09-01 19:56:15",
    "description": "",
    "url": "https://freesound.org/people/dobroide/packs/5107/",
    "user": {
        "username": "dobroide",
        "url": "https://freesound.org/people/dobroide/",
        "ref": "https://freesound.org/api/people/dobroide"
    },
    "sounds": "https://freesound.org/api/packs/5107/sounds",
    "num_downloads": 0,
    "ref": "https://freesound.org/api/packs/5107",
    "name": "Iceland"
  }




Pack Sounds collection
======================

URI
---

::

  /packs/<pack_id>/sounds

The only allowed method is GET.

GET
---

A paginated collection of the sounds in the pack.

Request
'''''''

**Parameters**

=========  ======  ========  ====================================
Name       Type    Required  Description
=========  ======  ========  ====================================
p          number  no        The page of the pack's sounds to get
fields	   string  no	     Fields
=========  ======  ========  ====================================

**Curl Examples**

::

  curl https://freesound.org/api/packs/5107/sounds

Response
''''''''

The response is the same as the :ref:`sound-search-response`.

