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

======================  =========================  ======================
Name                    Type                       Description
======================  =========================  ======================
``query``               string                     text
``filter``              string                     text
``sort``                string                     text
``group_by_pack``       bool (yes=1, no=0)         text
``page``                string                     text
``page_size``           string                     text
======================  =========================  ======================

.. _sound-list-response:

Response (sound list response)
------------------------------

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
called ``fields``, ``descriptors`` and ``normalized``. When these parameters are not specified, a minimal set of
information will be returned by default.


======================  =========================  ======================
Name                    Type                       Description
======================  =========================  ======================
``fields``              comma separated strings    Indicates which sound properties should be returned in the response.
``descirptors``         comma separated strings    Indicates which sound content-based descriptors should be returned in the response.
``normalized``          bool (yes=1, no=0)         Indicates whether the returned sound content-based descriptors should be normalized or not.
======================  =========================  ======================


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
