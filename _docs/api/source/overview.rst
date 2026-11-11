APIv2 Overview
>>>>>>>>>>>>>>

Welcome to the Freesound APIv2 documentation!

With the Freesound APIv2 you can browse, search, and retrieve information
about Freesound users, packs, and the sounds themselves of course. You
can find similar sounds to a given target (based on content analysis)
and retrieve automatically extracted features from audio files, as well as perform
advanced queries combining content analysis features and other metadata (tags, etc...).
With the Freesound APIv2, you can also upload, comment, rate and bookmark sounds!


Authentication
--------------

In order to start using APIv2 you'll need an API credential that you can request in https://freesound.org/apiv2/apply.
Basic API calls can be authenticated using a typical API key mechanism in which you'll need to add the key given with your APIv2
credential into every request you make. You'll need to add the key as a ``token`` request parameter.
For example:

::

  curl "https://freesound.org/apiv2/search/?query=piano&token=YOUR_API_KEY"

However, there are some APIv2 resources that require the use of OAuth2 authentication.
Please, read the :ref:`authentication` docs for a complete description of both authentication methods and how to use them.


Resources
---------

The Freesound APIv2 has plenty of resources allowing you to do a lot of stuff with Freesound data.
Here we just give an overview of the available resources, you will find the full documentation in  :ref:`resources`.


Searching
=========

There are several ways in which you can search sounds using the Freesound APIv2.
The most basic one is using the :ref:`sound-search` resource which allows you to define query terms and other parameters to filter query results.
As a quick example, the following request would return all sorts of dog sounds:

::

  curl "https://freesound.org/apiv2/search/?query=dogs&token=YOUR_API_KEY"


Search queries can include filters based on audio features (descriptors) rather than tags and textual metadata.
That means that you can retrieve sounds that, for example, have a particular pitch or bpm. These queries may include almost any of the audio features listed in :ref:`analysis-docs`.
Note however that these features are automatically extracted and might not be always accurate.
As a quick example, you can retrieve sounds that feature a particular pitch as follows:

::

  curl "https://freesound.org/apiv2/search/?filter=pitch:\[219.9%20TO%20220.1\]&token=YOUR_API_KEY"


Downloading sounds
==================

The Freesound API allows you to download sounds from Freesound.
There are two ways in which you can download sounds.
The first one is to download the original file that was uploaded to Freesound for a particular sound.
You can do that using the :ref:`sound-download` resource.
This resource allows you to retrieve the file in its maximum quality, but the format depends on the original format with which the sound was uploaded (it can be .wav, .aif, .flac, .ogg or .mp3).
Downloading original sound files requires OAuth2 authentication (see :ref:`authentication`).


The second way in which you can download sounds is by accessing their *previews*.
When sounds are uploaded to Freesound we automatically generate .ogg and .mp3 versions for each one with different qualities. We call these versions *previews*.
Using the :ref:`sound-sound` resource (or any resource that returns a list of sounds), it is possible to obtain the urls for retrieving sound previews.
In general, downloading previews is faster than downloading sounds in their original quality and allows your application to retrieve sounds in a consistent format.
Retrieving previews does not require OAuth2 authentication.


Uploading sounds
================

APIv2 also allows you to upload sounds to Freesound!
Sounds are uploaded by providing an audio file and metadata, which we call the *sound description*.
The minimum sound description consists of a category, a list of tags, a textual description, and a license.
You can upload and describe sounds using the :ref:`sound-upload` resource (requires OAuth2).
Alternatively, you can simply upload an audio file using the :ref:`sound-upload` resource, and later describe it using the :ref:`sound-describe` resource.

Take into account that all sounds in Freesound are automatically processed and **manually moderated** (including sounds uploaded using the APIv2).
This means that after sounds are uploaded and described, they still need to be processed and moderated before they appear in the Freesound web and can be further used in the APIv2.
Processing is an automatic step that is almost instantaneous, but moderation is done manually by a team of people and might take some days.
The Freesound APIv2 provides a resource, :ref:`sound-pending-uploads`, to keep track of the status of uploaded files.


Other resources
===============

The Freesound API also provides access to :ref:`sound analysis <sound-analysis>`,
:ref:`similar sounds <similar-sounds>`, :ref:`packs <pack_instance>`,
:ref:`users <user_instance>`, and :ref:`bookmarks <bookmark-categories>`.
See the :ref:`resources` page for the complete list.


Browsable API
-------------

The Freesound API includes a browsable interface for exploring resources and trying requests in your browser.

Visit https://freesound.org/apiv2/ and use the login link if you're not already logged in.
Once logged in, you can navigate the API interface without providing an API key.


POST request content types
--------------------------

In POST requests, we recommend to use ``multipart/form-data`` content-type and set the header accordingly.
For requests that do not include file uploads, we do also support ``application/json`` and ``application/x-www-form-urlencoded`` content-types.


Response Format
---------------

Responses are returned as JSON. You can request this explicitly with a ``format`` request parameter:

::

  https://freesound.org/apiv2/sounds/1234/?format=json

If the format is not specified, it will be automatically determined in the content-negotiation phase, typically defaulting to JSON.


Errors
------

If your requests are correctly processed and no errors occur, the APIv2 will return a response with a 200 OK status code.
However, if something goes wrong in your requests, the Freesound APIv2 will return error messages which can include the following status codes:

=========================  ====================================================================
HTTP code                  Explanation
=========================  ====================================================================
400 Bad request            The request was unsuccessful because the request is missing parameters or parameters are not properly formatted.
401 Unauthorized           The credentials you provided are invalid.
403 Forbidden              Mainly returned when resources that require HTTPS are accessed with plain HTTP requests.
404 Not found              The information that the request is trying to access does not exist.
405 Method not allowed     The current request method (generally GET or POST) is not supported by the resource.
409 Conflict               The request is valid but it cannot be processed for some reason detailed in the response.
429 Too many requests      The request was throttled because of exceeding request limit rates (see :ref:`overview-throttling`).
5xx                        An error on our part, hopefully you will see few of these.
=========================  ====================================================================

All error responses consist of a dictionary with a ``detail`` field that describes the error.
Make sure to check the contents of that field to better understand the nature of the error, particularly in 400 Bad request responses.


.. _overview-throttling:


Throttling
----------

The usage of the APIv2 is limited to certain usage rates.
The standard usage rate is set to 60 requests per minute and 2000 requests per day.
Resources including original quality sound downloading, uploading, describing, commenting, rating and bookmarking sounds have a more strict rate of 30 requests per minute and 500 requests per day.

If a request is throttled, the APIv2 will return a 429 Too many requests response error with a ``detail`` field indicating which rate limit has been exceeded.

Although we have set the default usage limits so that they should be enough for most applications,
if these usage limits are not enough for you, please contact Freesound administrators using the contact form (https://freesound.org/contact/) to request more permissive limits.

See the :ref:`Usage resource documentation <current-usage>` for more information about rate limits and your current usage.


More help
---------

If you need more help after reading these documents, want to stay up to
date on any changes or future features of the Freesound APIv2, or if you would
like to request more features for the API, please contact us using our google group:


- http://groups.google.com/group/freesound-api
