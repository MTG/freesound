APIv1 Documentation
>>>>>>>>>>>>>>>>>>>>

**NOTE**: Freesound APIv1 has reached its end of life and is no longer available.

Welcome to the Freesound API (V1) docs!

With the Freesound API you can browse, search, and retrieve information
about Freesound users, packs, and the sounds themselves of course. You
can also find similar sounds to a given target (based on content analysis)
and retrieve automatically extracted features from audio files.
Check out the available :ref:`resources_apiv1`.


Important information
---------------------

APIv1 is deprecated. It will continue working until the end of 2014, but from now on we recommend everyone
to start using APIv2.


More help
---------

If you need more help after reading these documents or want to stay up to
date on any changes or future features of the freesound api or if you would
like to request more features for the api, please use our google group:


- http://groups.google.com/group/freesound-api

RESTful
-------
The Freesound API is a so called RESTful API, meaning that all requests and
responses are done with standard HTTP requests.

Base URL
--------

All the REST resources mentioned in the documentation have the following
base URL.

::

  https://freesound.org/api

There is currently no support for HTTPS, only HTTP.

Authentication
--------------

All requests to the Freesound API need to be signed with your API key. At
present this is done simply by adding an 'api_key' GET parameter to the end of
the URI to be requested. A request to the sounds search resource with API key
``12d6dc5486554e278e370cdc49935908`` would look as follows.

::

  https://freesound.org/api/sounds/search?q=barking&api_key=12d6dc5486554e278e370cdc49935908

N.B. The URIs documented on these pages do not show the API keys, but they
are definitely necessary.

If authentication fails, you will get a response with status code
'401 Unauthorized' and the following content (indeed, all error responses have the same structure):

::

  {
    "status_code": 401,
    "explanation": "Supplied api_key does not exist",
    "type": "AuthenticationError",
    "error": true
  }

You can apply for API keys at the following URL. Note that you will need
a Freesound account.

- https://freesound.org/api/apply

Requests
--------

The documentation will show for each resource how to interact with them. In
REST you basically have four types of requests: GET, POST, PUT, and DELETE.
Note that not every resource supports all four types.

Resources are always identified by URIs. When the documentation shows a
variable URI (e.g. ``/sounds/<sound_id>``) the parameter indicated by the brackets
will have to be replaced to get a valid URI.

For example, the following URIs are all instances of the resource indicated by
``/sounds/<sound_id>``.

::

  https://freesound.org/api/sounds/18763
  https://freesound.org/api/sounds/11
  https://freesound.org/api/sounds/8734

Responses
---------

All the API responses consist of a HTTP status code and the response
itself. The status code indicates whether the request was successful
or that some error was encountered. The response body holds the data
if the request was successful or an error message if it was not.

Formats
_______

The format of the response can be specified in the request and can be
one of JSON, XML, YAML, and Pickle. We recommend using JSON, as this
is currently the only response format we actively test.

To specify the desired response format add a 'format' GET or POST parameter
to the request. Specify the desired format in lowercase letters as follows:

::

  # example requests for your files, but with different response formats
  https://freesound.org/api/sounds/search?api_key=12d6dc5486554e278e370cdc49935908&format=json
  https://freesound.org/api/sounds/search?api_key=12d6dc5486554e278e370cdc49935908&format=xml
  https://freesound.org/api/sounds/search?api_key=12d6dc5486554e278e370cdc49935908&format=yaml
  https://freesound.org/api/sounds/search?api_key=12d6dc5486554e278e370cdc49935908&format=pickle

N.B. The default format is JSON.

Status Codes
____________

It is very important to check the status code of the response and to not
assume the request was successful. The following status codes are
the codes that are used throughout the API.

=========================  ====================================================================
HTTP code                  Explanation
=========================  ====================================================================
200 OK                     Everything went as expected, the usual response for GET requests.
400 Bad Request            The request was unsuccessful, most likely because the request
    			   itself was invalid.
401 Unauthorized           The credentials you provided were wrong.
404 Not Found              The resource requested does not exist.
405 Method Not Allowed     For this resource this HTTP method does not make sense.
5xx                        An error on our part, hopefully you will see few of these.
=========================  ====================================================================


JSONP callback
--------------

Whenever you need a JSONP callback, add the parameter ``callback`` to the
request like so::

  ?callback=something

You're response will instead of::

  {a: 1}

become::

  something({a: 1})


Request Identification
----------------------

When performing multiple requests, the identification with its
particular response might become non trivial. For that purpose,
any request can be complemented with an optional parameter ``request_id``
that will also be included in the response. Just as an example:

::

  ?request_id=something

will return:

::

  {
     [...sounds, users, packs data...],
     "request_id": "something"
  }


API's Resources
---------------

Check out the :ref:`resources_apiv1`.


Clients Libraries
-----------------

Python
  https://github.com/g-roma/freesound-python/tree/APIv1

Javascript (recommended version)
  https://github.com/g-roma/freesound.js/tree/APIv1

Javascript (old version)
  https://github.com/ffont/freesound-javascript

As3 (Flash, Flex)
  https://github.com/ffont/freesound-flex

Php
  https://github.com/nocive/freesound-php (by nocive_)

.. _nocive: https://github.com/nocive

Supercollider
  Download through the Quarks system from within supercollider

C#
  https://github.com/EricSchayes/freesound-CSharp
