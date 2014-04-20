.. _resources:

Resources (APIv2)
<<<<<<<<<<<<<<<<<

Search resources
>>>>>>>>>>>>>>>>

Search
=========================================================

::

  GET /apiv2/search/

This resource allows searching sounds in Freesound by matching their tags and other kinds of metadata.

Request parameters (basic search parameters)
--------------------------------------------

Queries are defined using the following request parameters:

======================  =========================  ======================
Name                    Type                       Description
======================  =========================  ======================
``query``               string                     The query! The ``query`` is the main parameter used to define a query. You can type several terms separated by spaces or phrases wrapped inside quote '"' characters. For every term, you can also use '+' and '-' modifier characters to indicate that a term is "mandatory" or "prohibited" (by default, terms are considered to be "mandatory"). For example, in a query such as ``query=term_a -term_b``, sounds including ``term_b`` will not match the search criteria. The query does a weighted search over some sound properties including sound tags, the sound name, its description, pack name and the sound id. Therefore, searching for ``query=123`` will find you sounds with id 1234, sounds that have 1234 in the description, in tags, etc. You'll find some examples below.
``filter``              string                     Allows filtering query results. See below for more information.
``sort``                string                     Indicates how query results should be sorted. See below for a list of the sorting options. By default ``sort=score``.
``group_by_pack``       bool (yes=1, no=0)         This parameter represents a boolean option to indicate whether to collapse results belonging to sounds of the same pack into single entries in the results list. If ``group_by_pack=1`` and search results contain more than one sound that belongs to the same pack, only one sound for each distinct pack is returned (sounds with no packs are returned as well). However, the returned sound will feature two extra properties to access these other sounds omitted from the results list: ``n_from_same_pack``: indicates how many other results belong to the same pack (and have not been returned) ``more_from_same_pack``: uri pointing to the list of omitted sound results of the same pack (also including the result which has already been returned). By default ``group_by_pack=0``.
``page``                string                     Query results are paginated, this parameter indicates what page should be returned. By default ``page=1``.
``page_size``           string                     Indicates the number of sound to include in every query. By default ``page_size=30``, and the maximum is 100. Be careful with that parameter, bigger page sizes means that more data needs to be transferred.
======================  =========================  ======================


**The 'filter' parameter**

Search results can be filtered by specifying a series of properties that sounds should match.
In other words, using the ``filter`` parameter you can specify the value that certain sound fields should have in order to be considered valid search results.
Filter are defined as ``filter=fieldname:value fieldname:value`` or ``filter=fieldname:"value" fieldname:"value"`` if needed.
Fieldnames can be any of the following:


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
type: 			string, original file type ("wav", "aif", "aiff", "ogg", "mp3" or "flac")
duration: 		numerical, duration of sound in seconds
bitdepth: 		integer, WARNING is not to be trusted right now
bitrate: 		numerical, WARNING is not to be trusted right now
samplerate: 		integer
filesize: 		integer, file size in bytes
channels: 		integer, number of channels in sound (mostly 1 or 2)
md5: 			string, 32-byte md5 hash of file
num_downloads: 		integer
avg_rating: 		numerical, average rating, from 0 to 5
num_ratings: 		integer, number of ratings
comment: 		string, tokenized (filter is satisfied if sound contains the specified value in at least one of its comments)
comments: 		numerical, number of comments
======================  ====================================================

Numeric or integer filters can have a range as a query, looking like this (the "TO" needs
to be upper case!)::

  [start TO end]
  [* TO end]
  [start to \*]

Dates can have ranges (and math) too (the "TO" needs to be upper case!)::

  created:[* TO NOW]
  created:[1976-03-06T23:59:59.999Z TO *]
  created:[1995-12-31T23:59:59.999Z TO 2007-03-06T00:00:00Z]
  created:[NOW-1YEAR/DAY TO NOW/DAY+1DAY]
  created:[1976-03-06T23:59:59.999Z TO 1976-03-06T23:59:59.999Z+1YEAR]
  created:[1976-03-06T23:59:59.999Z/YEAR TO 1976-03-06T23:59:59.999Z]

Simple logic operators can also used in filters::

  type:(wav OR aiff)
  description:(piano AND note)

See below for some examples!


**The 'sort' parameter**

The ``sort`` parameter determines how the results are sorted, and can only be one
of the following.

==============  ====================================================================
Option          Explanation
==============  ====================================================================
score           Sort by a relevance score returned by our search engine (default).
duration_desc   Sort by the duration of the sounds, longest sounds first.
duration_asc    Same as above, but shortest sounds first.
created_desc    Sort by the date of when the sound was added. newest sounds first.
created_asc	    Same as above, but oldest sounds first.
downloads_desc  Sort by the number of downloads, most downloaded sounds first.
downloads_asc   Same as above, but least downloaded sounds first.
rating_desc     Sort by the average rating given to the sounds, highest rated first.
rating_asc      Same as above, but lowest rated sounds first.
==============  ====================================================================


**Using geotagging data in queries**

TODO... but you can already check the examples below ;)


.. _sound-list-response:

Response (sound list)
---------------------

Search resource returns a *sound list response*. Sound list responses have the following structure:

::

  {
    "count": <total number of results>,
    "next": <link to the next page of results (null if none)>,
    "results": [
        <sound result #1 info>,
        <sound result #2 info>,
        ...
    ],
    "previous": <link to the previous page of results (null if none)>
  }


Sound information that is returned for every sound in the results can be determined using extra request parameters
called ``fields``, ``descriptors`` and ``normalized``.

======================  =========================  ======================
Name                    Type                       Description
======================  =========================  ======================
``fields``              comma separated strings    Indicates which sound properties should be included in every sound of the response. Sound properties can be any of those listed in :ref:`sound-instance-response`, and must be separated by commas. For example, if ``fields=name,avg_rating,license``, results will include sound name, average rating and license for every returned sound. Use this parameter to optimize request times by only requesting the information you really need.
``descriptors``         comma separated strings    Indicates which sound content-based descriptors should be included in every sound of the response. This parameter must be used in combination with the ``fields`` parameter. If ``fields`` includes the property ``analysis``, you will use ``descriptors`` parameter to indicate which descriptors should be included in every sound of the response. Descriptors names can be any of those listed in :ref:`analysis-docs`, and must be separated by commas and start with a dot '.' character. For example, if ``fields=analysis&descriptors=.lowlevel.spectral_centroid,.lowlevel.barkbands.mean``, the response will include, for every returned sound, all statistics of the spectral centroid descriptor and the mean of the barkbands. Descriptor values are included in the response inside the ``analysis`` sound property (see the examples). ``analysis`` might be null if no valid descriptors names were found of the analysis data of a particular sound is not available.
``normalized``          bool (yes=1, no=0)         Indicates whether the returned sound content-based descriptors should be normalized or not. ``normalized=1`` will return normalized descriptor values. By default, ``normalized=0``.
======================  =========================  ======================

If ``fields``  is not specified, a minimal set of information is returned by default.
This includes information about the license and Freesound public url of the sound, and the uris of the sound itself, the user that uploaded it and its pack (in case the sound belongs to a pack).


Examples
--------

{{examples_Search}}



Advanced Search
=========================================================


::

  GET /apiv2/search/advanced/

Description.

Request parameters
------------------


Response
--------

Return a sound list just like :ref:`sound-list-response`.



Examples
--------

{{examples_AdvancedSearch}}


Sound resources
>>>>>>>>>>>>>>>


Sound Instance
=========================================================

::

  GET /apiv2/sounds/<sound_id>

This resource allows the retrieval of detailed information of a sound.

Detailed information can include content-based features by using an extra request parameter ``descriptors``.
``descriptors`` should include a comma separated list of descriptor names. Descriptors names can be any of those listed in :ref:`analysis-docs`, and must start with a dot '.' character (e.g. ``descriptors=.lowlevel.mfcc,.rhythm.bpm``, similar to what you would do to get descriptors in search responses :ref:`sound-list-response`).


.. _sound-instance-response:

Response (sound instance)
-------------------------

The sound instance response includes the following properties/fields:

====================  ================  ====================================================================================
Name                  Type              Description
====================  ================  ====================================================================================
id                    number            The sound's unique identifier.
uri                   URI               The URI for this sound.
url                   URI               The URI for this sound on the Freesound website.
name                  string            The name user gave to the sound.
tags                  array[strings]    An array of tags the user gave to the sound.
description           string            The description the user gave to the sound.
geotag                string            Latitude and longitude of the geotag separated by spaces (e.g. "41.0082325664 28.9731252193", only for sounds that have been geotagged).
created               string            The date of when the sound was uploaded.
license               string            The license under which the sound is available to you.
type                  string            The type of sound (wav, aif, aiff, mp3, or flac).
channels              number            The number of channels.
filesize              number            The size of the file in bytes.
bitrate               number            The bit rate of the sound in kbps.
bitdepth              number            The bit depth of the sound.
duration              number            The duration of the sound in seconds.
samplerate            number            The samplerate of the sound.
user                  URI               The URI for the uploader of the sound.
username              string            The username of the uploader of the sound.
pack                  URI               If the sound is part of a pack, this URI points to that pack's API resource.
download              URI               The URI for retrieving the original sound.
bookmark              URI               The URI for bookmarking the sound.
previews              object            Dictionary containing the URIs for mp3 and ogg versions of the sound. The dictionary includes the fields ``preview-hq-mp3`` and ``preview-lq-mp3`` (for ~128kbps quality and ~64kbps quality mp3 respectively), and ``preview-hq-ogg`` and ``preview-lq-ogg`` (for ~192kbps quality and ~80kbps quality ogg respectively).
images                object            Dictionary including the URIs for spectrogram and waveform visualizations of the sound. The dinctionary includes the fields ``waveform_l`` and ``waveform_m`` (for large and medium waveform images respectively), and ``spectral_l`` and ``spectral_m`` (for large and medium spectrogram images respectively).
num_downloads         number            The number of times the sound was downloaded.
avg_rating            number            The average rating of the sound.
num_ratings           number            The number of times the sound was rated.
rate                  URI               The URI for rating the sound.
comments              URI               The URI of a paginated list of the comments of the sound.
num_comments          number            The number of comments.
comment               URI               The URI to comment the sound.
similar_sounds        URI               URI pointing to the similarity resource (to get a list of similar sounds).
analysis              object            Object containing requested descriptors information. This field will be null if no descriptors were specified (or invalid descriptor names specified) or if the analysis data for the sound is not available.
analysis_stats        URI               URI pointing to the complete analysis results of the sound (see :ref:`analysis-docs`).
analysis_frames       URI               The URI for retrieving a JSON file with analysis information for each frame of the sound (see :ref:`analysis-docs`).
====================  ================  ====================================================================================


Examples
--------

{{examples_SoundInstance}}


Sound Analysis
=========================================================

Examples
--------

{{examples_SoundAnalysis}}


Similar Sounds
=========================================================

Examples
--------

{{examples_SimilarSounds}}


Sound Comments
=========================================================

Examples
--------

{{examples_SoundComments}}


Download Sound (OAuth2 required)
=========================================================

::

  GET /apiv2/sounds/{{sound_id}}/download/

This resource allows you to download a sound in its original format/quality (the format/quality with which the sound was uploaded).
It requires :ref:`oauth-authentication`.

Examples
--------

{{examples_DownloadSound}}


Upload Sound (OAuth2 required)
=========================================================

Examples
--------

{{examples_UploadSound}}


Not Yet Described Uploaded Sounds (OAuth2 required)
=========================================================

Examples
--------

{{examples_NotYetDescribedUploadedSounds}}


Describe Sound (OAuth2 required)
=========================================================

Examples
--------

{{examples_DescribeSound}}


Upload and Describe Sound (OAuth2 required)
=========================================================

Examples
--------

{{examples_UploadAndDescribeSound}}


Uploaded Sounds awaiting moderation in Freesound (OAuth2 required)
==================================================================

Examples
--------

{{examples_UploadedAndDescribedSoundsPendingModeration}}


Bookmark Sound (OAuth2 required)
=========================================================

Examples
--------

{{examples_BookmarkSound}}


Rate Sound (OAuth2 required)
=========================================================

Examples
--------

{{examples_RateSound}}


Comment Sound (OAuth2 required)
=========================================================

Examples
--------

{{examples_CommentSound}}



User resources
>>>>>>>>>>>>>>


User Instance
=========================================================

Examples
--------

{{examples_UserInstance}}


User Sounds
=========================================================

Examples
--------

{{examples_UserSounds}}



User Packs
=========================================================

Examples
--------

{{examples_UserPacks}}


User Bookmark Categories
=========================================================

Examples
--------

{{examples_UserBookmarkCategories}}


User Bookmark Category Sounds
=========================================================

Examples
--------

{{examples_UserBookmarkCategorySounds}}



Me (information about user authenticated using OAuth2, OAuth2 required)
=======================================================================

.. _me_resource:

This resource...


Pack resources
>>>>>>>>>>>>>>


Pack Instance
=========================================================

Examples
--------

{{examples_PackInstance}}


Pack Sounds
=========================================================

Examples
--------

{{examples_PackSounds}}


Download Pack (OAuth2 required)
=========================================================

Examples
--------

{{examples_DownloadPack}}
