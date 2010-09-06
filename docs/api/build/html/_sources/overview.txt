Overview
>>>>>>>>

With the Freesound API you can browse, search, and retrieve information 
about Freesound users, packs, and the sounds themselves of course.
Currently, the API is read only. We might add features for uploading
sounds in the future.

RESTful
-------
The Freesound API is a so called RESTful API, meaning that all requests and
responses are done with standard HTTP requests.

To read about REST design principles we recommend TODO.

Base URL
--------

All the REST resources mentioned in the documentation have the following
base URL.

::

  http://www.freesound.org/api

There is currently no support for HTTPS, only HTTP.

Authentication
--------------

All requests to the Freesound API need to be signed with your API key. At
present this is done simply by adding an 'api_key' GET parameter to the end of
the URI to be requested. A request to the sounds search resource with API key
``12d6dc5486554e278e370cdc49935908`` would look as follows.

::

  http://www.freesound.org/api/sounds/search?q=barking&api_key=12d6dc5486554e278e370cdc49935908

N.B. The URIs documented on these pages do not show the API keys, but they
are definitely necessary.

If authentication fails, you will get a response with status code
'401 Unauthorized'.

You can apply for API keys at the following URL. Note that you will need 
a Freesound account.

- http://www.freesound.org/api/apply

Requests
--------

The documentation will show for each resource how to interact with it. In
REST you basically have four types of requests: GET, POST, PUT, and DELETE.
Note that not every resource supports all four types.

Resources are always identified by URIs. When the documentation shows a
variable URI (e.g. ``/sounds/<sound_id>``) the parameter indicated by the brackets
will have to be replaced to get a valid URI.

For example, the following URIs are all instances of the resource indicated by
``/sounds/<sound_id>``.

::

  http://www.freesound.org/api/0132dfd197c84db6a8e56012b2e08d02
  http://www.freesound.org/api/ceda30d8d2cf41eb9a156c7ef288fc54
  http://www.freesound.org/api/89116d024cf34dc38f269e6b9abb2db5
  http://www.freesound.org/api/800b2b9ba3884d0092575d9631c58921


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
  http://api.canoris.com/files?api_key=12d6dc5486554e278e370cdc49935908&format=json
  http://api.canoris.com/files?api_key=12d6dc5486554e278e370cdc49935908&format=xml
  http://api.canoris.com/files?api_key=12d6dc5486554e278e370cdc49935908&format=yaml
  http://api.canoris.com/files?api_key=12d6dc5486554e278e370cdc49935908&format=pickle

N.B. The default format is JSON.

Status Codes
____________

It is very important to check the status code of the response and to not
assume the request has been successful. The following status codes are 
the codes that are used throughout the API.

=========================  =============================================================================================================
HTTP code                  Explanation
=========================  =============================================================================================================
200 OK                     Everything went as expected, the usual response for GET requests.
400 Bad Request            The request was unsuccessful, most likely because the request itself was invalid.
401 Unauthorized           The credentials you provided were wrong.
404 Not Found              The resource requested does not exist.
405 Method Not Allowed     For this resource this HTTP method does not make sense.
5xx                        An error on our part, hopefully you will see few of these.
=========================  =============================================================================================================

API's Resources
---------------

Check out the API's :ref:`resources`.
