.. _resources:

Resources (APIv2)
<<<<<<<<<<<<<<<<<

.. contents::
    :depth: 3


Search resources
>>>>>>>>>>>>>>>>

.. _sound-text-search:

Text Search
=========================================================

::

  GET /apiv2/search/text/

This resource allows searching sounds in Freesound by matching their tags and other kinds of metadata.

.. _sound-text-search-parameters:

Request parameters (text search parameters)
-------------------------------------------

Text search queries are defined using the following request parameters:

======================  =========================  ======================
Name                    Type                       Description
======================  =========================  ======================
``query``               string                     The query! The ``query`` is the main parameter used to define a query. You can type several terms separated by spaces or phrases wrapped inside quote '"' characters. For every term, you can also use '+' and '-' modifier characters to indicate that a term is "mandatory" or "prohibited" (by default, terms are considered to be "mandatory"). For example, in a query such as ``query=term_a -term_b``, sounds including ``term_b`` will not match the search criteria. The query does a weighted search over some sound properties including sound tags, the sound name, its description, pack name and the sound id. Therefore, searching for ``query=123`` will find you sounds with id 1234, sounds that have 1234 in the description, in tags, etc. You'll find some examples below.
``filter``              string                     Allows filtering query results. See below for more information.
``sort``                string                     Indicates how query results should be sorted. See below for a list of the sorting options. By default ``sort=score``.
``group_by_pack``       bool (yes=1, no=0)         This parameter represents a boolean option to indicate whether to collapse results belonging to sounds of the same pack into single entries in the results list. If ``group_by_pack=1`` and search results contain more than one sound that belongs to the same pack, only one sound for each distinct pack is returned (sounds with no packs are returned as well). However, the returned sound will feature two extra properties to access these other sounds omitted from the results list: ``n_from_same_pack``: indicates how many other results belong to the same pack (and have not been returned) ``more_from_same_pack``: uri pointing to the list of omitted sound results of the same pack (also including the result which has already been returned). By default ``group_by_pack=0``.
======================  =========================  ======================


**The 'filter' parameter**

Search results can be filtered by specifying a series of properties that sounds should match.
In other words, using the ``filter`` parameter you can specify the value that certain sound fields should have in order to be considered valid search results.
Filter are defined with a syntax like ``filter=fieldname:value fieldname:value`` or ``filter=fieldname:"value" fieldname:"value"`` if needed.
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

  filter=fieldname:[start TO end]
  filter=fieldname:[* TO end]
  filter=fieldname:[start to \*]

Dates can have ranges (and math) too (the "TO" needs to be upper case!)::

  filter=created:[* TO NOW]
  filter=created:[1976-03-06T23:59:59.999Z TO *]
  filter=created:[1995-12-31T23:59:59.999Z TO 2007-03-06T00:00:00Z]
  filter=created:[NOW-1YEAR/DAY TO NOW/DAY+1DAY]
  filter=created:[1976-03-06T23:59:59.999Z TO 1976-03-06T23:59:59.999Z+1YEAR]
  filter=created:[1976-03-06T23:59:59.999Z/YEAR TO 1976-03-06T23:59:59.999Z]

Simple logic operators can also used in filters::

  filter=type:(wav OR aiff)
  filter=description:(piano AND note)

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


There are some extra request parameters that you can use to determine some of the contents of the sound list response.
These parameters are ``page`` and ``page_size`` (to deal with pagination), and ``fields``, ``descriptors`` and ``normalized`` to deal with the sound information that is returned for every sound in the results.

======================  =========================  ======================
Name                    Type                       Description
======================  =========================  ======================
``page``                string                     Query results are paginated, this parameter indicates what page should be returned. By default ``page=1``.
``page_size``           string                     Indicates the number of sounds per page to include in the result. By default ``page_size=15``, and the maximum is ``page_size=15``. Not that with bigger ``page_size``, more data will need to be transferred.
``fields``              comma separated strings    Indicates which sound properties should be included in every sound of the response. Sound properties can be any of those listed in :ref:`sound-instance-response`, and must be separated by commas. For example, if ``fields=name,avg_rating,license``, results will include sound name, average rating and license for every returned sound. Use this parameter to optimize request times by only requesting the information you really need.
``descriptors``         comma separated strings    Indicates which sound content-based descriptors should be included in every sound of the response. This parameter must be used in combination with the ``fields`` parameter. If ``fields`` includes the property ``analysis``, you will use ``descriptors`` parameter to indicate which descriptors should be included in every sound of the response. Descriptor names can be any of those listed in :ref:`analysis-docs`, and must be separated by commas. For example, if ``fields=analysis&descriptors=lowlevel.spectral_centroid,lowlevel.barkbands.mean``, the response will include, for every returned sound, all statistics of the spectral centroid descriptor and the mean of the barkbands. Descriptor values are included in the response inside the ``analysis`` sound property (see the examples). ``analysis`` might be null if no valid descriptor names were found of the analysis data of a particular sound is not available.
``normalized``          bool (yes=1, no=0)         Indicates whether the returned sound content-based descriptors should be normalized or not. ``normalized=1`` will return normalized descriptor values. By default, ``normalized=0``.
======================  =========================  ======================

If ``fields``  is not specified, a minimal set of information is returned by default.
This includes information about the license and Freesound public url of the sound, and the uris of the sound itself, the user that uploaded it and its pack (in case the sound belongs to a pack).


Examples
--------

{{examples_TextSearch}}



.. _sound-content-search:

Content Search
=========================================================

::

  GET /apiv2/search/content/
  POST /apiv2/search/content/

This resource allows searching sounds in Freesound based on their content descriptors.


.. _sound-content-search-parameters:

Request parameters (content search parameters)
----------------------------------------------

Content search queries are defined using the following request parameters:

=========================  =========================  ======================
Name                       Type                       Description
=========================  =========================  ======================
``target``                 string or number           This parameter defines a target based on content-based descriptors to sort the search results. It can be set as a number of descriptor name and value pairs or a sound id. See below.
``analysis_file``          file                       Alternatively, targets can be specified using file with the output of the Essentia Freesound Extractor analysis of any sound (see below). This parameter overrides ``target``, and requires the use of POST method.
``descriptors_filer``      string                     This parameter allows filtering query results by values of the content-based descriptors. See below for more information.
=========================  =========================  ======================

**The 'target' and 'analysis_file' parameters**

The ``target`` parameter can be used to specify a content-based sorting of your search results.
Using ``target`` you can sort the query results so that the first results will the the ones featuring the most similar descriptors to the given target.
To specify a target you must use a syntax like ``target=descriptor_name:value``.
You can also set multiple descriptor/value paris in a target separating them with spaces (``target=descriptor_name:value descriptor_name:value``).
Descriptor names must be chosen from those listed in :ref:`analysis-docs`. Only numerical descriptors are allowed.
Multidimensional descriptors with fixed-length (that always have the same number of dimensions) are allowed too, see below.
Consider the following two ``target`` examples::

  (A) target=.lowlevel.pitch.mean:220
  (B) target=.lowlevel.pitch.mean:220 .lowlevel.pitch.var:0

Example A will sort the query results so that the first results will have a mean pitch as closest to 220Hz as possible.
Example B will sort the query results so that the first results will have a mean pitch as closest to 220Hz as possible and a pitch variance as closes as possible to 0.
In that case example B will promote sounds that have a steady pitch close to 220Hz.

Multidimensional descriptors can also be used in the ``target`` parameter::

  target=.sfx.tristimulus.mean:0,1,0

Alternatively, ``target`` can also be set to point to a Freesound sound.
In that case the descriptors of the sound will be used as the target for the query, therefore query results will be sorted according to their similarity to the targeted sound.
To set a sound as a target of the query you must indicate it with the sound id. For example, to use sound with id 1234 as target::

  target=1234


There is even another way to specify a target for the query, which is by uploading an analysis file generated using the Essentia Freesound Extractor.
For doing that you will need to download and compile Essentia, an open source feature extraction library developed at the Music Technology Group (https://github.com/mtg/essentia),
and use the 'streaming_extractor_freesound' example to analyze any sound you have in your local computer.
As a result, the extractor will create a JSON file that you can use as target in your Freesound API content search queries.
To use this file as target you will need to use the POST method (instead of GET) and attach the file as an ``analysis_file`` POST parameter (see example below).
Setting the target as an ``analysis_file`` allows you to to find sounds in Freesound that are similar to any other sound that you have in your local computer and that it is not part of Freesound.
When using ``analysis_file``, the contents of ``target`` are ignored.

If ``target`` (or ``analysis_file``) is not used in combination with ``descriptors_filter``, the results of the query will
include all sounds from Freesound indexed in the similarity server.


**The 'descriptors_filer' parameter**

The ``descriptors_filter`` parameter is used to restrict the query results to those sounds whose content descriptor values comply with the defined filter.
To define ``descriptors_filter`` parameter you can use the same syntax as for the normal ``filter`` parameter, including numeric ranges and simple logic operators.
For example, ``descriptors_filter=.lowlevel.pitch.mean:220`` will only return sounds that have an EXACT pitch mean of 220hz.
Note that this would probably return no results as a sound will rarely have that exact pitch (might be very close like 219.999 or 220.000001 but not exactly 220).
For this reason, in general it might be better to indicate ``descriptors_filter`` using ranges.
Descriptor names must be chosen from those listed in :ref:`analysis-docs`.
Note that most of the descriptors provide several statistics (var, mean, min, max...). In that case, the descriptor name must include also the desired statistic (see examples below).
Non fixed-length descriptors are not allowed.
Some examples of ``descriptors_filter`` for numerical descriptors::

  descriptors_filter=.lowlevel.pitch.mean:[219.9 TO 220.1]
  descriptors_filter=.lowlevel.pitch.mean:[219.9 TO 220.1] AND .lowlevel.pitch_salience.mean:[0.6 TO *]
  descriptors_filter=.lowlevel.mfcc.mean[0]:[-1124 TO -1121]
  descriptors_filter=.lowlevel.mfcc.mean[1]:[17 TO 20] AND .lowlevel.mfcc.mean[4]:[0 TO 20]

Note how in the last two examples the filter operates in a particular dimension of a multidimensional descriptor (with dimension index starting at 0).

``descriptors_filter`` can also be defined using non numerical descriptors such as '.tonal.key_key' or '.tonal.key_scale'.
In that case, the value but be enclosed in double quotes '"', and the character '#' (for example for an A# key) must be indicated with the string 'sharp'.
Non numerical descriptors can not be indicated using ranges.
For example::

  descriptors_filter=.tonal.key_key:"Asharp"
  descriptors_filter=.tonal.key_scale:"major"
  descriptors_filter=(.tonal.key_key:"C" AND .tonal.key_scale:"major") OR (.tonal.key_key:"A" AND .tonal.key_scale:"minor")

You can combine both numerical and non numerical descriptors as well::

  descriptors_filter=.tonal.key_key:"C" .tonal.key_scale="major" .tonal.key_strength:[0.8 TO *]




Response
--------

The Content Search resource returns a sound list just like :ref:`sound-list-response`.
The same extra request parameters apply (``page``, ``page_size``, ``fields``, ``descriptors`` and ``normalized``).


Examples
--------

{{examples_ContentSearch}}


.. _sound-combined-search:

Combined Search
=========================================================

::

  GET /apiv2/search/combined/
  POST /apiv2/search/combined/

This resource is a combination of :ref:`sound-text-search` and :ref:`sound-content-search`, and allows searching sounds in Freesound based on their tags, metadata and content-based descriptors.


Request parameters
------------------

Combined search request parameters can include any of the parameters from text-based search queries (``query``, ``filter`` and ``sort``, :ref:`sound-text-search-parameters`)
and content-based search queries (``target``, ``analysis_file`` and ``descriptors_filer`` and, :ref:`sound-content-search-parameters`).
Note that ``group_by_pack`` **is not** available in combined search queries.

In combined search, queries can be defined both like a standard textual query or as a target of content-descriptors, and
query results can be filtered either by values of sounds' metadata or sounds' content-descriptors... all at once!

To perform a combined search query you need to use at least one of the request parameters from text-based search and at least one of the request parameters from content-based search.
Note that ``sort`` parameter must always be accompanied by a ``query`` or ``filter`` parameter (or both), otherwise it is ignored.
``sort`` parameter will also be ignored if parameter ``target`` (or ``analysis_file``) is present in the query.


Response
--------

The Combined Search resource returns a sound list just like :ref:`sound-list-response`.
The same extra request parameters apply (``page``, ``page_size``, ``fields``, ``descriptors`` and ``normalized``).



Examples
--------

{{examples_CombinedSearch}}


Sound resources
>>>>>>>>>>>>>>>


Sound Instance
=========================================================

::

  GET /apiv2/sounds/<sound_id>/

This resource allows the retrieval of detailed information about a sound.


.. _sound-instance-response:

Response (sound instance)
-------------------------

The Sound Instance response is a dictionary including the following properties/fields:

====================  ================  ====================================================================================
Name                  Type              Description
====================  ================  ====================================================================================
``id``                number            The sound's unique identifier.
``uri``               URI               The URI for this sound.
``url``               URI               The URI for this sound on the Freesound website.
``name``              string            The name user gave to the sound.
``tags``              array[strings]    An array of tags the user gave to the sound.
``description``       string            The description the user gave to the sound.
``geotag``            string            Latitude and longitude of the geotag separated by spaces (e.g. "41.0082325664 28.9731252193", only for sounds that have been geotagged).
``created``           string            The date when the sound was uploaded (e.g. "2014-04-16T20:07:11.145").
``license``           string            The license under which the sound is available to you.
``type``              string            The type of sound (wav, aif, aiff, mp3, or flac).
``channels``          number            The number of channels.
``filesize``          number            The size of the file in bytes.
``bitrate``           number            The bit rate of the sound in kbps.
``bitdepth``          number            The bit depth of the sound.
``duration``          number            The duration of the sound in seconds.
``samplerate``        number            The samplerate of the sound.
``user``              URI               The URI for the uploader of the sound.
``username``          string            The username of the uploader of the sound.
``pack``              URI               If the sound is part of a pack, this URI points to that pack's API resource.
``download``          URI               The URI for retrieving the original sound.
``bookmark``          URI               The URI for bookmarking the sound.
``previews``          object            Dictionary containing the URIs for mp3 and ogg versions of the sound. The dictionary includes the fields ``preview-hq-mp3`` and ``preview-lq-mp3`` (for ~128kbps quality and ~64kbps quality mp3 respectively), and ``preview-hq-ogg`` and ``preview-lq-ogg`` (for ~192kbps quality and ~80kbps quality ogg respectively).
``images``            object            Dictionary including the URIs for spectrogram and waveform visualizations of the sound. The dinctionary includes the fields ``waveform_l`` and ``waveform_m`` (for large and medium waveform images respectively), and ``spectral_l`` and ``spectral_m`` (for large and medium spectrogram images respectively).
``num_downloads``     number            The number of times the sound was downloaded.
``avg_rating``        number            The average rating of the sound.
``num_ratings``       number            The number of times the sound was rated.
``rate``              URI               The URI for rating the sound.
``comments``          URI               The URI of a paginated list of the comments of the sound.
``num_comments``      number            The number of comments.
``comment``           URI               The URI to comment the sound.
``similar_sounds``    URI               URI pointing to the similarity resource (to get a list of similar sounds).
``analysis``          object            Object containing requested descriptors information according to the ``descriptors`` request parameter (see below). This field will be null if no descriptors were specified (or invalid descriptor names specified) or if the analysis data for the sound is not available.
``analysis_stats``    URI               URI pointing to the complete analysis results of the sound (see :ref:`analysis-docs`).
``analysis_frames``   URI               The URI for retrieving a JSON file with analysis information for each frame of the sound (see :ref:`analysis-docs`).
====================  ================  ====================================================================================


The contents of the field ``analysis`` of the Sound Instance response can be determined using an additional request parameter ``descriptors``.
The ``descriptors`` parameter should include a comma separated list of content-based descriptor names, just like in the :ref:`sound-list-response`.
Descriptor names can be any of those listed in :ref:`analysis-docs` (e.g. ``descriptors=lowlevel.mfcc,rhythm.bpm``).
The request parameter ``normalized`` can also be used to return content-based descriptor values in a normalized range instead of the absolute values.

The parameter ``fields`` can also be used to restrict the number of fields returned in the response.


Examples
--------

{{examples_SoundInstance}}


Sound Analysis
=========================================================

::

  GET /apiv2/sounds/<sound_id>/analysis/

This resource allows the retrieval of analysis information (content-based descriptors) of a sound.
Although content-based descriptors can also be retrieved using the ``descriptors`` request parameter in any API resource that returns sound lists or with the Sound Instance resource,
using the Sound Analysis resource you can retrieve **all sound descriptors** at once.


Response
--------

The response to a Sound Analysis request is a dictionary with the values of all content-based descriptors listed in :ref:`analysis-docs`.
That dictionary can be filtered using an extra ``descriptors`` request parameter which should include a list of comma separated descriptor names chosen from those listed in :ref:`analysis-docs` (e.g. ``descriptors=lowlevel.mfcc,rhythm.bpm``).
The request parameter ``normalized`` can also be used to return content-based descriptor values in a normalized range instead of the absolute values.


Examples
--------

{{examples_SoundAnalysis}}


Similar Sounds
=========================================================

::

  GET /apiv2/sounds/<sound_id>/similar/

This resource allows the retrieval of sounds similar to the given target.


Request parameters
------------------

Essentially, the Similar Sounds resource is like a :ref:`sound-content-search` resource with the parameter ``target`` fixed to the sound id indicated in the url.
You can still use the ``descriptors_filter`` request parameter to restrict the query results to those sounds whose content descriptor values comply with the defined filter.
Use ``descriptors_filter`` in the same way as in :ref:`sound-content-search` and :ref:`sound-combined-search` resources.



Response
--------

Similar Sounds resource returns a sound list just like :ref:`sound-list-response`.
The same extra request parameters apply (``page``, ``page_size``, ``fields``, ``descriptors`` and ``normalized``).


Examples
--------

{{examples_SimilarSounds}}


Sound Comments
=========================================================

::

  GET /apiv2/sounds/<sound_id>/comments/

This resource allows the retrieval of the comments of a sound.


Response
--------

Sound Comments resource returns a paginated list of the comments of a sound, with a similar structure as :ref:`sound-list-response`:

::

  {
    "count": <total number of comments>,
    "next": <link to the next page of comments (null if none)>,
    "results": [
        <most recent comment for sound_id>,
        <second most recent comment for sound_id>,
        ...
    ],
    "previous": <link to the previous page of comments (null if none)>
  }

Comments are sorted according to their creation date (recent comments in the top of the list).
Parameters ``page`` and ``page_size`` can be used just like in :ref:`sound-list-response` to deal with the pagination of the response.

Each comment entry consists of a dictionary with the following structure:

::

  {
    "user": "<uri of user who made the comment>",
    "comment": "<the comment itself>",
    "created": "<the date when the comment was made, e.g. "2014-03-15T14:06:48.022">"
  }



Examples
--------

{{examples_SoundComments}}


Download Sound (OAuth2 required)
=========================================================

::

  GET /apiv2/sounds/<sound_id>/download/

This resource allows you to download a sound in its original format/quality (the format/quality with which the sound was uploaded).
It requires :ref:`oauth-authentication`.

Examples
--------

{{examples_DownloadSound}}


.. _sound-upload:

Upload Sound (OAuth2 required)
=========================================================

::

  POST /apiv2/sounds/upload/

This resource allows you to upload an audio file into Freesound.
Note that this resource is only meant for uploading an audio file, not for describing it.
In order for the file to appear in Freesound, it must be described using the :ref:`sound-describe` resource (after uploading),
and it must be processed and moderated by the Freesound moderators just like any other sound uploaded using the Freessound website rather than the API.
A list of uploaded files pending description can be obtained using the :ref:`sound-uploaded-files-pending-description` resource.

The author of the uploaded sound will be the user authenticated via Oauth2, therefore this method requires :ref:`oauth-authentication`.


Request parameters
------------------

The uploaded audio file must be attached to the request as a ``audiofile`` POST parameter.
Supported file formats include .wav, .aif, .flac, .ogg and .mp3.


Response
--------

On successful upload, the Upload Sound resource will return a dictionary with the following structure:

::

  {
    "details": "File successfully uploaded (<file size>)",
    "filename": "<filename of the uploaded audio file>"
  }

You will probably want to store the content of the ``filename`` field because it will be needed to later describe the sound.
Alternatively, you can obtain a list of uploaded sounds pending description using the :ref:`sound-uploaded-files-pending-description` resource.


Examples
--------

{{examples_UploadSound}}

.. _sound-uploaded-files-pending-description:

Uploads Pending Description (OAuth2 required)
=========================================================

::

  GET /apiv2/sounds/not_yet_described/

This resource allows you to retrieve a list of audio files uploaded by a the Freesound user logged in using OAuth2 that have not yet been described.
This method requires :ref:`oauth-authentication`.


Response
--------

The Uploads Pending Description resource returns a dictionary with the following structure:

::

  {
    "filenames": [
        "<filename #1>",
        "<filename #2>",
        ...
    ]
  }

The filenames returned by this resource are used as file identifiers in the :ref:`sound-describe` resource.


Examples
--------

{{examples_NotYetDescribedUploadedSounds}}


.. _sound-describe:

Describe Sound (OAuth2 required)
=========================================================

::

  POST /apiv2/sounds/describe/

This resource allows you to describe a previously uploaded audio file.
This method requires :ref:`oauth-authentication`.
Note that after a sound is described, it still needs to be processed and moderated by the team of Freesound moderators, therefore it will not yet appear in Freesound.
You can obtain a list of sounds uploaded and described by the user logged in using OAuth2 but still pending processing and moderation using the :ref:`sound-pending-moderation` resource.


Request parameters
------------------

A request to the Describe Sound resource must include the following POST parameters:

====================  ================  ====================================================================================
Name                  Type              Description
====================  ================  ====================================================================================
``upload_filename``   string            The filename of the sound to describe. Must match with one of the filenames returned in :ref:`sound-uploaded-files-pending-description` resource.
``name``              string            (OPTIONAL) The name that will be given to the sound. If not provided, filename will be used.
``tags``              string            The tags that will be assigned to the sound. Separate tags with spaces and join multi-words with dashes (e.g. "tag1 tag2 tag3 cool-tag4").
``description``       string            A textual description of the sound.
``license``           string            The license of the sound. Must be either "Attribution", "Attribution Noncommercial" or "Creative Commons 0".
``pack``              string            (OPTIONAL) The name of the pack where the sound should be included. If user has created no such pack with that name, a new one will be created.
``geotag``            string            (OPTIONAL) Geotag information for the sound. Latitude, longitude and zoom values in the form lat,lon,zoom (e.g. "2.145677,3.22345,14").
====================  ================  ====================================================================================


Response
--------

If the audio file is described successfully, the Describe Sound resource will return a dictionary with the following structure:

::

  {
    "details": "Sound successfully described (now pending moderation)",
    "uri": "<URI of the described sound instance>"
  }

Note that after the sound is described, it still needs to be processed and moderated by the team of Freesound moderators.
Therefore, the url returned in parameter ``uri`` will lead to a 404 Not Found error until the sound is approved by the moderators.

If some of the required fields are missing or some of the provided fields are badly formatted, a 400 Bad Request response will be returned describing the errors.


Examples
--------

{{examples_DescribeSound}}


.. _sound-edit-description:


Edit Sound Description (OAuth2 required)
=========================================================

::

  POST /apiv2/sounds/<sound_id>/edit/

This resource allows you to edit the description of an already existing sound.
Note that this resource can only be used to edit descriptions of sounds created by the Freesound user logged in using OAuth2.
This method requires :ref:`oauth-authentication`.


Request parameters
------------------

A request to the Edit Sound Description resource must include mostly the same POST parameters that would be included in a :ref:`sound-describe` request:

====================  ================  ====================================================================================
Name                  Type              Description
====================  ================  ====================================================================================
``name``              string            (OPTIONAL) The new name that will be given to the sound.
``tags``              string            (OPTIONAL) The new tags that will be assigned to the sound. Note that if this parameter is filled, old tags will be deleted. Separate tags with spaces and join multi-words with dashes (e.g. "tag1 tag2 tag3 cool-tag4").
``description``       string            (OPTIONAL) The new textual description for the sound.
``license``           string            (OPTIONAL) The new license of the sound. Must be either "Attribution", "Attribution Noncommercial" or "Creative Commons 0".
``pack``              string            (OPTIONAL) The new name of the pack where the sound should be included. If user has created no such pack with that name, a new one will be created.
``geotag``            string            (OPTIONAL) New geotag information for the sound. Latitude, longitude and zoom values in the form lat,lon,zoom (e.g. "2.145677,3.22345,14").
====================  ================  ====================================================================================

Note that for that resource all parameters are optional.
Only the fields included in the request will be used to update the sound description
(e.g. if only ``name`` and ``tags`` are included in the request, these are the only properties that will be updated from sound description,
the others will remain unchanged).


Response
--------

If sound description is updated successfully, the Edit Sound Description resource will return a dictionary with the following structure:

::

  {
    "details": "Description of sound <sound_id> successfully edited",
    "uri": "<URI of the described sound instance>"
  }


If some of the required fields are missing or some of the provided fields are badly formatted, a 400 Bad Request response will be returned describing the errors.





.. _sound-pending-moderation:

Uploaded Sounds Awaiting Moderation in Freesound (OAuth2 required)
==================================================================

::

  GET /apiv2/sounds/uploads_pending_moderation/

This resource allows you to retrieve a list of sounds that have been uploaded and described by the user logged in using OAuth2, but that still need to be processed and moderated.
This method requires :ref:`oauth-authentication`.

Response
--------

The response to the Uploaded Sounds Awaiting Moderation in Freesound resource is a dictionary with the following structure:

::

  {
    "sounds pending processing": [
        <sound #1>,
        <sound #2>,
        ...
    ],
    "sounds pending moderation": [
        <sound #1>,
        <sound #2>,
        ...
    ],
  }

Each sound entry either in "sounds pending processing" or "sounds pending moderation" fields consists of a minimal set
of information about that sound including the ``name``, ``tags``, ``description``, ``created`` and ``license`` fields
that you would find in a :ref:`sound-instance-response`.
Sounds under "sounds pending moderation" also contain an extra ``images`` field containing the uris of the waveform and spectrogram
images of the sound as described in :ref:`sound-instance-response`.

Processing is done automatically in Freesound right after sounds are described, and it normally takes less than a minute.
Therefore, you should normally see that the list of sounds under "sounds pending processing" is empty.


Examples
--------

{{examples_UploadedAndDescribedSoundsPendingModeration}}


.. _sound-upload-and-describe:

Upload and Describe Sound (OAuth2 required)
=========================================================

::

  POST /apiv2/sounds/upload_and_describe/

This resource allows you to upload an audio file into Freesound and describe it at once.
In order for the file to appear in Freesound, it will still need to be processed and moderated by the Freesound moderators
just like any other sound uploaded using the Freessound website rather than the API.
The author of the uploaded sound will be the user authenticated via Oauth2, therefore this method requires :ref:`oauth-authentication`.

A list of uploaded and described sounds pending processing and moderation can be obtained using the :ref:`sound-pending-moderation` resource.

Request
-------

A request to the Upload and Describe Sound resource must include the same POST parameters as in :ref:`sound-describe`,
with the exception that instead of the parameter ``upload_filename``, you must attach an audio file using an ``audiofile`` parameter like in :ref:`sound-upload`.
Supported file formats include .wav, .aif, .flac, .ogg and .mp3.

Response
--------

If the audio file is upload and described successfully, the Upload and Describe Sound resource will return a dictionary with the following structure:

::

  {
    "details": "Audio file successfully uploaded and described (now pending moderation)",
    "uri": "<URI of the uploaded and described sound instance>"
  }

Note that after the sound is uploaded and described, it still needs to be processed and moderated by the team of Freesound moderators.
Therefore, the url returned in parameter ``uri`` will lead to a 404 Not Found error until the sound is approved by the moderators.

If some of the required fields are missing or some of the provided fields are badly formatted, a 400 Bad Request response will be returned describing the errors.



Examples
--------

{{examples_UploadAndDescribeSound}}


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

.. _user_instance:

User Instance
=========================================================

::

  GET /apiv2/users/<username>/

This resource allows the retrieval of information about a particular Freesound user.


Response
--------

The User Instance response is a dictionary including the following properties/fields:

========================  ================  ====================================================================================
Name                      Type              Description
========================  ================  ====================================================================================
``uri``                   URI               The URI for this user.
``url``                   URI               The URI for this users' profile on the Freesound website.
``username``              string            The username.
``about``                 string            The 'about' text of users' profile (if indicated).
``homepage``              URI               The URI of users' homepage outside Freesound (if indicated).
``avatar``                object            Dictionary including the URIs for the avatar of the user. The avatar is presented in three sizes ``Small``, ``Medium`` and ``Large``, which correspond to the three fields in the dictionary. If user has no avatar, this field is null.
``date_joined``           string            The date when the user joined Freesound (e.g. "2008-08-07T17:39:00").
``num_sounds``            number            The number of sounds uploaded by the user.
``sounds``                URI               The URI for a list of sounds by the user.
``num_packs``             number            The number of packs by the user.
``packs``                 URI               The URI for a list of packs by the user.
``num_posts``             number            The number of forum posts by the user.
``num_comments``          number            The number of comments that user made in other users' sounds.
``bookmark_categories``   URI               The URI for a list of bookmark categories by the user.
========================  ================  ====================================================================================


Examples
--------

{{examples_UserInstance}}


User Sounds
=========================================================

::

  GET /apiv2/users/<username>/sounds/

This resource allows the retrieval of a list of sounds uploaded by a particular Freesound user.


Response
--------

Similar Sounds resource returns a sound list just like :ref:`sound-list-response`.
The same extra request parameters apply (``page``, ``page_size``, ``fields``, ``descriptors`` and ``normalized``).

Examples
--------

{{examples_UserSounds}}



User Packs
=========================================================

::

  GET /apiv2/users/<username>/packs/

This resource allows the retrieval of a list of packs created by a particular Freesound user.


Response
--------

User Packs resource returns a paginated list of the packs created by a user, with a similar structure as :ref:`sound-list-response`:

::

  {
    "count": <total number of packs>,
    "next": <link to the next page of packs (null if none)>,
    "results": [
        <most recent pack created by the user>,
        <second most recent pack created by the user>,
        ...
    ],
    "previous": <link to the previous page of packs (null if none)>
  }

Each pack entry consists of a dictionary with the same fields returned in the :ref:`pack-instance`: response.
Packs are sorted according to their creation date (recent packs in the top of the list).
Parameters ``page`` and ``page_size`` can be used just like in :ref:`sound-list-response` to deal with the pagination of the response.




Examples
--------

{{examples_UserPacks}}


User Bookmark Categories
=========================================================

::

  GET /apiv2/users/<username>/bookmark_categories/

This resource allows the retrieval of a list of bookmark categories created by a particular Freesound user.


Response
--------

User Bookmark Categories resource returns a paginated list of the bookmark categories created by a user, with a similar structure as :ref:`sound-list-response`:

::

  {
    "count": <total number of bookmark categories>,
    "next": <link to the next page of bookmark categories (null if none)>,
    "results": [
        <first bookmark category>,
        <second bookmark category>,
        ...
    ],
    "previous": <link to the previous page of bookmark categories (null if none)>
  }

Parameters ``page`` and ``page_size`` can be used just like in :ref:`sound-list-response` to deal with the pagination of the response.

Each bookmark category entry consists of a dictionary with the following structure:

::

  {
    "url": "<URI of the bookmark category in Freesound>",
    "name": "<name that the user has given to the bookmark category>",
    "num_sounds": <number of sounds under the bookmark category>,
    "sounds": "<URI to a page with the list of sounds in this bookmark category>",
  }


Examples
--------

{{examples_UserBookmarkCategories}}


User Bookmark Category Sounds
=========================================================

::

  GET /apiv2/users/<username>/bookmark_categories/<bookmark_category_id>/sounds/

This resource allows the retrieval of a list of sounds from a bookmark category created by a particular Freesound user.

Response
--------

User Bookmark Category Sounds resource returns a sound list just like :ref:`sound-list-response`.
The same extra request parameters apply (``page``, ``page_size``, ``fields``, ``descriptors`` and ``normalized``).

Examples
--------

{{examples_UserBookmarkCategorySounds}}


Me (information about user authenticated using OAuth2, OAuth2 required)
=======================================================================

.. _me_resource:

::

  GET /apiv2/me/

This resource returns basic information of a user that has logged in using the Oauth2 procedure.
It can be used by applications to be able to identify which Freesound user has logged in.

Response
--------

The Me resource response consists of a dictionary with all the fields present in a standard :ref:`user_instance`, plus an additional ``email`` field that can be used by the application to uniquely identify the end user.


Pack resources
>>>>>>>>>>>>>>


.. _pack_instance:

Pack Instance
=========================================================

::

  GET /apiv2/packs/<pack_id>/

This resource allows the retrieval of information about a pack.


Response
--------

The Pack Instance response is a dictionary including the following properties/fields:

====================  ================  ====================================================================================
Name                  Type              Description
====================  ================  ====================================================================================
``id``                number            The unique identifier of this pack.
``uri``               URI               The URI for this pack.
``url``               URI               The URI for this pack on the Freesound website.
``description``       string            The description the user gave to the pack (if any).
``created``           string            The date when the pack was created (e.g. "2014-04-16T20:07:11.145").
``name``              string            The name user gave to the pack.
``num_sounds``        number            The number of sounds in the pack.
``sounds``            URI               The URI for a list of sounds in the pack.
``num_downloads``     number            The number of times this pack has been downloaded.
====================  ================  ====================================================================================


Examples
--------

{{examples_PackInstance}}


Pack Sounds
=========================================================

::

  GET /apiv2/packs/<pack_id>/

This resource allows the retrieval of the list of sounds included in a pack.

Response
--------

Pack Sounds resource returns a sound list just like :ref:`sound-list-response`.
The same extra request parameters apply (``page``, ``page_size``, ``fields``, ``descriptors`` and ``normalized``).

Examples
--------

{{examples_PackSounds}}


Download Pack (OAuth2 required)
=========================================================

::

  GET /apiv2/packs/<pack_id>/download/

This resource allows you to download all the sounds of a pack in a single zip file.
It requires :ref:`oauth-authentication`.

Examples
--------

{{examples_DownloadPack}}
