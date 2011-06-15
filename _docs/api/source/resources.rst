.. _resources:

Resources
<<<<<<<<<

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

=========  ======  ========  =================================
Name       Type    Required  Description
=========  ======  ========  =================================
q	   string  no        The query!
p          number  no        The page of the search result to get
f          string  no	     The filter
s	   string  no	     How to sort the results
=========  ======  ========  =================================

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
license: 		string
is_remix: 		boolean
was_remixed: 		boolean
pack: 			string
pack_tokenized: 	string, tokenized
is_geotagged: 		boolean
type: 			string, original file type, one of wav,
    			aiff, ogg, mp3, flac
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
duration_desc   Sort by the duration of the sounds, longest sounds first.
duration_asc    Same as above, but shortest sounds first.
created_desc    Sort by the date of when the sound was added. newest sounds first.
created_asc	Same as above, but oldest sounds first.
downloads_desc  Sort by the number of downloads, most downloaded sounds first.
downloads_asc   Same as above, but least downloaded sounds first.
rating_desc     Sort by the average rating given to the sounds, highest rated first.
rating_asc      Same as above, but lowest rated sounds first.
==============  ====================================================================

**Curl Examples**

::

  # Get the third page with the query 'dogs', with the most downloaded sounds first.
  curl http://tabasco.upf.edu/api/sounds/search?p=3&q=dogs&s=downloads_desc
  # Get the most recent uploaded sounds with the tag 'synth' and querying for 'bass'
  curl http://tabasco.upf.edu/api/sounds/search?q=bass&f=tag:synth&s=created_desc
  # Get short kick sounds
  curl http://tabasco.upf.edu/api/sounds/search?q=kick&f=duration:[0.1 TO 0.3]


.. _sound-search-response:

Response
''''''''

**Properties**

===========  =======  ===========================================================================================
Name         Type     Description
===========  =======  ===========================================================================================
sounds       array    Array of sounds. Each sound looks like a reduced version of the `response format of a single sound resource`__. (with less information)
num_results  int      Number of sounds found that match your search
num_pages    int      Number of pages (as the result is paginated)
previous     URI      The URI to go back one page in the search results.
next         URI      The URI to go forward one page in the search results.
===========  =======  ===========================================================================================

__ sound-get-response_

**JSON Example**

::

  {
    "num_results": 810, 
    "sounds": [
        {
            "analysis_stats": "http://tabasco.upf.edu/api/sounds/116841/analysis", 
            "analysis_frames": "http://tabasco.upf.edu/data/analysis/116/116841_854810_frames.json", 
            "waveform_m": "http://tabasco.upf.edu/data/displays/116/116841_854810_wave_M.png", 
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
            "url": "http://tabasco.upf.edu/people/toiletrolltube/sounds/116841/", 
            "preview-hq-ogg": "http://tabasco.upf.edu/data/previews/116/116841_854810-hq.ogg", 
            "serve": "http://tabasco.upf.edu/api/sounds/116841/serve", 
            "similarity": "http://tabasco.upf.edu/api/sounds/116841/similar", 
            "preview-lq-ogg": "http://tabasco.upf.edu/data/previews/116/116841_854810-lq.ogg", 
            "spectral_m": "http://tabasco.upf.edu/data/displays/116/116841_854810_spec_M.jpg", 
            "preview-lq-mp3": "http://tabasco.upf.edu/data/previews/116/116841_854810-lq.mp3", 
            "user": {
                "username": "toiletrolltube", 
                "url": "http://tabasco.upf.edu/people/toiletrolltube/", 
                "ref": "http://tabasco.upf.edu/api/people/toiletrolltube"
            }, 
            "spectral_l": "http://tabasco.upf.edu/data/displays/116/116841_854810_spec_L.jpg", 
            "duration": 5.6986699999999999, 
            "waveform_l": "http://tabasco.upf.edu/data/displays/116/116841_854810_wave_L.png", 
            "ref": "http://tabasco.upf.edu/api/sounds/116841", 
            "id": 116841, 
            "preview-hq-mp3": "http://tabasco.upf.edu/data/previews/116/116841_854810-hq.mp3", 
            "pack": "http://tabasco.upf.edu/api/packs/7333"
        },
        [...more sounds...]
        {
            "analysis_stats": "http://tabasco.upf.edu/api/sounds/113785/analysis", 
            "analysis_frames": "http://tabasco.upf.edu/data/analysis/113/113785_1956076_frames.json", 
            "waveform_m": "http://tabasco.upf.edu/data/displays/113/113785_1956076_wave_M.png", 
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
            "url": "http://tabasco.upf.edu/people/Puniho/sounds/113785/", 
            "preview-hq-ogg": "http://tabasco.upf.edu/data/previews/113/113785_1956076-hq.ogg", 
            "serve": "http://tabasco.upf.edu/api/sounds/113785/serve", 
            "similarity": "http://tabasco.upf.edu/api/sounds/113785/similar", 
            "preview-hq-mp3": "http://tabasco.upf.edu/data/previews/113/113785_1956076-hq.mp3", 
            "spectral_m": "http://tabasco.upf.edu/data/displays/113/113785_1956076_spec_M.jpg", 
            "preview-lq-mp3": "http://tabasco.upf.edu/data/previews/113/113785_1956076-lq.mp3", 
            "user": {
                "username": "Puniho", 
                "url": "http://tabasco.upf.edu/people/Puniho/", 
                "ref": "http://tabasco.upf.edu/api/people/Puniho"
            }, 
            "spectral_l": "http://tabasco.upf.edu/data/displays/113/113785_1956076_spec_L.jpg", 
            "duration": 2.6059399999999999, 
            "waveform_l": "http://tabasco.upf.edu/data/displays/113/113785_1956076_wave_L.png", 
            "ref": "http://tabasco.upf.edu/api/sounds/113785", 
            "id": 113785, 
            "preview-lq-ogg": "http://tabasco.upf.edu/data/previews/113/113785_1956076-lq.ogg"
        }
    ], 
    "previous": "http://tabasco.upf.edu/api/sounds/search?q=dogs&p=1&f=&s=downloads_desc", 
    "num_pages": 27, 
    "next": "http://tabasco.upf.edu/api/sounds/search?q=dogs&p=3&f=&s=downloads_desc"
  }



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

  curl http://tabasco.upf.edu/api/sounds/83295

.. _sound-get-response:

Response
''''''''

**Properties**

====================  =======  ====================================================================================
Name                  Type     Description
====================  =======  ====================================================================================
id                    number   The sound's unique identifier.
ref                   URI      The URI for this sound.
url                   URI      The URI for this sound on the Freesound website.
preview-hq-mp3        URI      The URI for retrieving a high quality (~128kbps) mp3 preview of the sound.
preview-lq-mp3        URI      The URI for retrieving a low quality (~64kbps) mp3 preview of the sound.
preview-hq-ogg        URI      The URI for retrieving a high quality (~192kbps) ogg preview of the sound.
preview-lq-ogg        URI      The URI for retrieving a low quality (~80kbps) ogg of the sound.
serve                 URI      The URI for retrieving the original sound.
similarity            URI      URI pointing to the similarity resource (to get a list of similar sounds).
type                  string   The type of sound (wav, aif, mp3, etc.).
duration              number   The duration of the sound in seconds.
samplerate            number   The samplerate of the sound.
bitdepth              number   The bit depth of the sound.
filesize              number   The size of the file in bytes.
bitrate               number   The bit rate of the sound in kbps.
channels              number   The number of channels.
original_filename     string   The name of the sound file when it was uploaded.
description           string   The description the user gave the sound.
tags                  array    An array of tags the user gave the sound.
license               string   The license under which the sound is available to you.
created               string   The date of when the sound was uploaded.
num_comments          number   The number of comments.
num_downloads         number   The number of times the sound was downloaded.
num_ratings           number   The number of times the sound was rated.
avg_rating            number   The average rating of the sound.
pack                  URI      If the sound is part of a pack, this URI points to that pack's API resource.
user                  object   A dictionary with the username, url, and ref for the user that uploaded the sound.
spectral_m            URI      A visualization of the sounds spectrum over time, jpeg file (medium).
spectral_l            URI      A visualization of the sounds spectrum over time, jpeg file (large).
waveform_m            URI      A visualization of the sounds waveform, png file (medium).
waveform_l            URI      A visualization of the sounds waveform, png file (large).
analysis              URI      URI pointing to the analysis results of the sound (see :ref:`analysis-docs`).
analysis_frames       URI      The URI for retrieving a JSON file with analysis information for each frame of the sound (see :ref:`analysis-docs`).
====================  =======  ====================================================================================

**JSON Example**

::

  {
    "num_ratings": 0, 
    "duration": 260.98849999999999, 
    "samplerate": 44000.0, 
    "preview-hq-ogg": "http://tabasco.upf.edu/data/previews/17/17185_18799-hq.ogg", 
    "id": 17185, 
    "preview-lq-ogg": "http://tabasco.upf.edu/data/previews/17/17185_18799-lq.ogg", 
    "bitdepth": 16, 
    "num_comments": 0, 
    "filesize": 45934020, 
    "preview-hq-mp3": "http://tabasco.upf.edu/data/previews/17/17185_18799-hq.mp3", 
    "type": "wav", 
    "analysis_stats": "http://tabasco.upf.edu/api/sounds/17185/analysis", 
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
    "serve": "http://tabasco.upf.edu/api/sounds/17185/serve", 
    "similarity": "http://tabasco.upf.edu/api/sounds/17185/similar", 
    "spectral_m": "http://tabasco.upf.edu/data/displays/17/17185_18799_spec_M.jpg", 
    "spectral_l": "http://tabasco.upf.edu/data/displays/17/17185_18799_spec_L.jpg", 
    "user": {
        "username": "reinsamba", 
        "url": "http://tabasco.upf.edu/people/reinsamba/", 
        "ref": "http://tabasco.upf.edu/api/people/reinsamba"
    }, 
    "bitrate": 1408, 
    "num_downloads": 0, 
    "analysis_frames": "http://tabasco.upf.edu/data/analysis/17/17185_18799_frames.json", 
    "channels": 2, 
    "license": "http://creativecommons.org/licenses/sampling+/1.0/", 
    "created": "2006-03-19 23:53:37", 
    "url": "http://tabasco.upf.edu/people/reinsamba/sounds/17185/", 
    "ref": "http://tabasco.upf.edu/api/sounds/17185", 
    "avg_rating": 0.0, 
    "preview-lq-mp3": "http://tabasco.upf.edu/data/previews/17/17185_18799-lq.mp3", 
    "original_filename": "Nightingale song 3.wav", 
    "waveform_l": "http://tabasco.upf.edu/data/displays/17/17185_18799_wave_L.png", 
    "waveform_m": "http://tabasco.upf.edu/data/displays/17/17185_18799_wave_M.png", 
    "pack": "http://tabasco.upf.edu/api/packs/455"
  }



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
=========  ======  ========  ===================================================

**Curl Examples**

::

  # For the complete analysis result
  curl http://tabasco.upf.edu/sounds/999/analysis
  # For a filtered analysis result, in this case the analyzed average loudness
  curl http://tabasco.upf.edu/api/sounds/999/analysis/lowlevel/average_loudness/
  # Or for all the tonal data
  curl http://tabasco.upf.edu/api/sounds/999/analysis/tonal

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

  http://tabasco.upf.edu/data/analysis/17/17185_18799_frames.json



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
``preset`` parameter can be set to indicate which kind of similarity measure must be used when computing the distance.

Request
'''''''

**Parameters**

===========  ======  ========  ===================================================
Name         Type    Required  Description
===========  ======  ========  ===================================================
num_results  number  no        The number of similar sounds to return (max = 100, default = 15)
preset       string  no        The similarity measure to use when retrieving similar sounds [``music``, ``lowlevel``] (default = ``music``)
===========  ======  ========  ===================================================

**Curl Examples**

::

  # Get the most similar sound to 120597 with the preset for "musical" sounds (num_results equals 2 because original sound is also returned in the list)
  curl http://tabasco.upf.edu/api/sounds/120597/similar?num_results=2&preset=music
  # Get the 15 most similar sounds to 11 with the preset "lowlevel"
  curl http://tabasco.upf.edu/api/sounds/11/similar?preset=lowlevel

Response
''''''''

The response is the same as the `sound search response`__ but with the addition of a ``distance`` property (for each sound) resembling a numerical value of "dissimilarity" respect to the query sound (then, the first sound of the result will always have distance = 0.0).
If the response is an empty list (0 results), this is because the query sound has been recently uploaded and it has not still been indexed in the similarity database.

__ sound-search-response_

**JSON Example**

::

  {
    "sounds": [
        {
            "analysis_stats": "http://tabasco.upf.edu/api/sounds/11/analysis", 
            "preview-lq-ogg": "http://tabasco.upf.edu/data/previews/0/11_2-lq.ogg", 
            "tags": [
                "generated", 
                "sinusoid", 
                "sweep", 
                "clean"
            ], 
            "url": "http://tabasco.upf.edu/people/Bram/sounds/11/", 
            "ref": "http://tabasco.upf.edu/api/sounds/11",
            "id": 11, 
            "preview-lq-mp3": "http://tabasco.upf.edu/data/previews/0/11_2-lq.mp3", 
            "serve": "http://tabasco.upf.edu/api/sounds/11/serve", 
            "similarity": "http://tabasco.upf.edu/api/sounds/11/similar", 
            "pack": "http://tabasco.upf.edu/api/packs/2", 
            "distance": 0.0, 
            "spectral_m": "http://tabasco.upf.edu/data/displays/0/11_2_spec_M.jpg", 
            "spectral_l": "http://tabasco.upf.edu/data/displays/0/11_2_spec_L.jpg", 
            "user": {
                "username": "Bram", 
                "url": "http://tabasco.upf.edu/people/Bram/", 
                "ref": "http://tabasco.upf.edu/api/people/Bram"
            }, 
            "original_filename": "sweep_log.wav", 
            "type": "wav", 
            "duration": 2.0, 
            "analysis_frames": "http://tabasco.upf.edu/data/analysis/0/11_2_frames.json", 
            "waveform_l": "http://tabasco.upf.edu/data/displays/0/11_2_wave_L.png", 
            "waveform_m": "http://tabasco.upf.edu/data/displays/0/11_2_wave_M.png", 
            "preview-hq-ogg": "http://tabasco.upf.edu/data/previews/0/11_2-hq.ogg", 
            "preview-hq-mp3": "http://tabasco.upf.edu/data/previews/0/11_2-hq.mp3"
        }, 
        {
            "analysis_stats": "http://tabasco.upf.edu/api/sounds/104551/analysis", 
            "preview-lq-ogg": "http://tabasco.upf.edu/data/previews/104/104551_420640-lq.ogg", 
            "tags": [
                "attack", 
                "air", 
                "falling", 
                "war", 
                "drop", 
                "bomb", 
                "whistle"
            ], 
            "url": "http://tabasco.upf.edu/people/club%20sound/sounds/104551/", 
            "ref": "http://tabasco.upf.edu/api/sounds/104551", 
            "id": 104551, 
            "preview-lq-mp3": "http://tabasco.upf.edu/data/previews/104/104551_420640-lq.mp3", 
            "serve": "http://tabasco.upf.edu/api/sounds/104551/serve", 
            "similarity": "http://tabasco.upf.edu/api/sounds/104551/similar", 
            "pack": "http://tabasco.upf.edu/api/packs/6609", 
            "distance": 7122293096448.0, 
            "spectral_m": "http://tabasco.upf.edu/data/displays/104/104551_420640_spec_M.jpg", 
            "spectral_l": "http://tabasco.upf.edu/data/displays/104/104551_420640_spec_L.jpg", 
            "user": {
                "username": "club sound", 
                "url": "http://tabasco.upf.edu/people/club%20sound/", 
                "ref": "http://tabasco.upf.edu/api/people/club%20sound"
            }, 
            "original_filename": "Bomb Whistle long.wav", 
            "type": "wav", 
            "duration": 30.036799999999999, 
            "analysis_frames": "http://tabasco.upf.edu/data/analysis/104/104551_420640_frames.json", 
            "waveform_l": "http://tabasco.upf.edu/data/displays/104/104551_420640_wave_L.png", 
            "waveform_m": "http://tabasco.upf.edu/data/displays/104/104551_420640_wave_M.png", 
            "preview-hq-ogg": "http://tabasco.upf.edu/data/previews/104/104551_420640-hq.ogg", 
            "preview-hq-mp3": "http://tabasco.upf.edu/data/previews/104/104551_420640-hq.mp3"
        }, 
        {
            "analysis_stats": "http://tabasco.upf.edu/api/sounds/17052/analysis", 
            "preview-lq-ogg": "http://tabasco.upf.edu/data/previews/17/17052_4942-lq.ogg", 
            "tags": [
                "sweep", 
                "electronic", 
                "sound", 
                "supercollider"
            ], 
            "url": "http://tabasco.upf.edu/people/schluppipuppie/sounds/17052/", 
            "ref": "http://tabasco.upf.edu/api/sounds/17052",
            "id": 17052,  
            "preview-lq-mp3": "http://tabasco.upf.edu/data/previews/17/17052_4942-lq.mp3", 
            "serve": "http://tabasco.upf.edu/api/sounds/17052/serve", 
            "similarity": "http://tabasco.upf.edu/api/sounds/17052/similar", 
            "pack": "http://tabasco.upf.edu/api/packs/954", 
            "distance": 161591534288896.0, 
            "spectral_m": "http://tabasco.upf.edu/data/displays/17/17052_4942_spec_M.jpg", 
            "spectral_l": "http://tabasco.upf.edu/data/displays/17/17052_4942_spec_L.jpg", 
            "user": {
                "username": "schluppipuppie", 
                "url": "http://tabasco.upf.edu/people/schluppipuppie/", 
                "ref": "http://tabasco.upf.edu/api/people/schluppipuppie"
            }, 
            "original_filename": "sweep03_careful.aif", 
            "type": "aif", 
            "duration": 40.106299999999997, 
            "analysis_frames": "http://tabasco.upf.edu/data/analysis/17/17052_4942_frames.json", 
            "waveform_l": "http://tabasco.upf.edu/data/displays/17/17052_4942_wave_L.png", 
            "waveform_m": "http://tabasco.upf.edu/data/displays/17/17052_4942_wave_M.png", 
            "preview-hq-ogg": "http://tabasco.upf.edu/data/previews/17/17052_4942-hq.ogg", 
            "preview-hq-mp3": "http://tabasco.upf.edu/data/previews/17/17052_4942-hq.mp3"
        }, 
        {
            "analysis_stats": "http://tabasco.upf.edu/api/sounds/93063/analysis", 
            "preview-lq-ogg": "http://tabasco.upf.edu/data/previews/93/93063_926020-lq.ogg", 
            "tags": [
                "impulse"
            ], 
            "url": "http://tabasco.upf.edu/people/simonbshelley/sounds/93063/", 
            "ref": "http://tabasco.upf.edu/api/sounds/93063",
            "id": 93063,  
            "preview-lq-mp3": "http://tabasco.upf.edu/data/previews/93/93063_926020-lq.mp3", 
            "serve": "http://tabasco.upf.edu/api/sounds/93063/serve", 
            "similarity": "http://tabasco.upf.edu/api/sounds/93063/similar", 
            "distance": 350841315786752.0, 
            "spectral_m": "http://tabasco.upf.edu/data/displays/93/93063_926020_spec_M.jpg", 
            "spectral_l": "http://tabasco.upf.edu/data/displays/93/93063_926020_spec_L.jpg", 
            "user": {
                "username": "simonbshelley", 
                "url": "http://tabasco.upf.edu/people/simonbshelley/", 
                "ref": "http://tabasco.upf.edu/api/people/simonbshelley"
            }, 
            "original_filename": "sound source.wav", 
            "type": "wav", 
            "duration": 25.0, 
            "analysis_frames": "http://tabasco.upf.edu/data/analysis/93/93063_926020_frames.json", 
            "waveform_l": "http://tabasco.upf.edu/data/displays/93/93063_926020_wave_L.png", 
            "waveform_m": "http://tabasco.upf.edu/data/displays/93/93063_926020_wave_M.png", 
            "preview-hq-ogg": "http://tabasco.upf.edu/data/previews/93/93063_926020-hq.ogg", 
            "preview-hq-mp3": "http://tabasco.upf.edu/data/previews/93/93063_926020-hq.mp3"
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

  curl http://tabasco.upf.edu/api/people/Jovica
  curl http://tabasco.upf.edu/api/people/klankschap


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
first_name	      string   The user's first name, possibly empty.
last_name	      string   The user's last name, possibly empty.
about		      string   A small text the user wrote about himself.
home_page	      URI      The user's homepage, possibly empty.
signature	      string   The user's signature, possibly empty.
date_joined	      string   The date the user joined Freesound.
====================  =======  ========================================================


**JSON Example**

::

  {
    "username": "Jovica", 
    "first_name": "", 
    "last_name": "", 
    "packs": "http://tabasco.upf.edu/api/people/Jovica/packs", 
    "url": "http://tabasco.upf.edu/people/Jovica/", 
    "about": "Policy of use: you must state somewhere somehow (credit lines, web page, whatever) that the Freesound Project served this sounds. It is irrelevant to me whether you mention or not my authorship. Can't credit? Send me a personal message. (Thanks to dobroide for these words!)\r\n\r\nIf possible, I would also like to hear where the sounds are used, so if you can send me a link or something else, please do so. Thanks!\r\n\r\nCurrently adding LAYERS & DISTOPIA sample packs!\r\n\r\nFor some more information about me, click on the links below:\r\n<a href=\"http://www.myspace.com/jovicastorer\" rel=\"nofollow\">http://www.myspace.com/jovicastorer</a>\r\n\r\nAnd this is an experimental droney label for which I do some producing, engineering, mixing and mastering:\r\n<a href=\"http://www.plaguerecordings.com/index.htm\" rel=\"nofollow\">http://www.plaguerecordings.com/index.htm</a>\r\n\r\nCurrently me and a good friend of mine are working on a new <strong>c-o-l-o-u-r-s</strong> website. \r\n\r\nThe first release, <strong>'gekarameliseerd'</strong> by <strong>Jovica Storer</strong>, is available on:\r\n- emusic: <a href=\"http://www.emusic.com/album/Jovica-Storer-Gekarameliseerd-MP3-Download/11666781.html\" rel=\"nofollow\">http://www.emusic.com/album/Jovica-Storer-Gekarameliseerd-MP3-Download/11666781.html</a>\r\n- iTunes: <a href=\"http://itunes.apple.com/WebObjects/MZStore.woa/wa/viewAlbum?i=333466000&id;=333464878&s;=143443&uo;=6\" rel=\"nofollow\">http://itunes.apple.com/WebObjects/MZStore.woa/wa/viewAlbum?i=333466000&id;=333464878&s;=143443&uo;=6</a>\r\n- Napster: <a href=\"http://free.napster.com/view/album/index.html?id=13373722\" rel=\"nofollow\">http://free.napster.com/view/album/index.html?id=13373722</a>\r\nPlease check it out and if you want to support me, buy some tracks. Many thanks! \r\n\r\nNamaste!\r\nJovica Storer", 
    "home_page": "http://www.ampcast.com/music/25765/artist.php", 
    "signature": "Namaste!\r\nJovica Storer\r\n<a href=\"http://www.c-o-l-o-u-r-s.com\" rel=\"nofollow\">http://www.c-o-l-o-u-r-s.com</a>", 
    "sounds": "http://tabasco.upf.edu/api/people/Jovica/sounds", 
    "ref": "http://tabasco.upf.edu/api/people/Jovica", 
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

=========  ======  ========  ========================================
Name       Type    Required  Description
=========  ======  ========  ========================================
p          number  no        The page of the sound collection to get.
=========  ======  ========  ========================================

**Curl Examples**

::

  curl http://tabasco.upf.edu/api/people/thanvannispen/sounds
  curl http://tabasco.upf.edu/api/people/inchadney/sounds?p=5

Response
''''''''

The response is the same as the `sound search response`__.

__ sound-search-response_





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

  curl http://tabasco.upf.edu/api/people/dobroide/packs

Response
''''''''

**Properties**

The response is an array. Each item in the array follows a reduced version of the `pack resource format`__.

__ pack-get-response_


**JSON Example**

::

  {
    "num_results": 47, 
    "packs": [
        {
            "description": "", 
            "created": "2009-09-28 09:50:08", 
            "url": "http://tabasco.upf.edu/people/dobroide/packs/5266/", 
            "sounds": "http://tabasco.upf.edu/api/packs/5266/sounds", 
            "num_downloads": 0, 
            "ref": "http://tabasco.upf.edu/api/packs/5266", 
            "name": "scrub"
        }, 
        {
            "description": "", 
            "created": "2009-09-20 10:55:32", 
            "url": "http://tabasco.upf.edu/people/dobroide/packs/5230/", 
            "sounds": "http://tabasco.upf.edu/api/packs/5230/sounds", 
            "num_downloads": 0, 
            "ref": "http://tabasco.upf.edu/api/packs/5230", 
            "name": "granada"
        }
    ]
  }




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

  curl http://tabasco.upf.edu/api/packs/5107

.. _pack-get-response:

Response
''''''''

**Properties**

====================  =======  ========================================================
Name                  Type     Description
====================  =======  ========================================================
ref		      URI      The URI for this resource.
url		      URI      The URL for this pack's page on the Freesound website.
sounds		      URI      The API URI for the pack's sound collection.
user		      object   A JSON object with the user's username, url, and ref.
name		      string   The pack's name.
created		      string   The date when the pack was created.
num_downloads	      number   The number of times the pack was downloaded.
====================  =======  ========================================================

**JSON Example**

::

  {
    "created": "2009-09-01 19:56:15", 
    "url": "http://tabasco.upf.edu/people/dobroide/packs/5107/", 
    "user": {
        "username": "dobroide", 
        "url": "http://tabasco.upf.edu/people/dobroide/", 
        "ref": "http://tabasco.upf.edu/api/people/dobroide"
    }, 
    "sounds": "http://tabasco.upf.edu/api/packs/5107/sounds", 
    "num_downloads": 0, 
    "ref": "http://tabasco.upf.edu/api/packs/5107", 
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
=========  ======  ========  ====================================

**Curl Examples**

::

  curl http://tabasco.upf.edu/api/packs/5107/sounds

Response
''''''''

The response is the same as the `sound search response`__.

__ sound-search-response_

