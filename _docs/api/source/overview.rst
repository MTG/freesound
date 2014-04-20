Overview (APIv2)
>>>>>>>>>>>>>>>>

Welcome to the Freesound APIv2 documentation!

With the Freesound APIv2 you can browse, search, and retrieve information
about Freesound users, packs, and the sounds themselves of course. You
can find similar sounds to a given target (based on content analysis)
and retrieve automatically extracted features from audio files, as well as perform
advanced queries combining content analysis features and other metadata (tags, etc...).
With the Freesound APIv2, you can also upload, comment, rate and bookmark sounds!

Freesound APIv2 is **still in a beta phase** so it might not be completely reliable.
Documentation is still incomplete and we haven't released any client libraries yet.
Therefore, use it at your own risk! ;)

NOTE: Some of the examples in the API docummentation use the multi-platform command-line tool ``curl`` (http://curl.haxx.se).
If you do not have ``curl`` installed, we recommend you to install it as it will help you in learning to use the Freesound API.


Resources
---------

To quickly understand how APIv2 works and which resources it offers, we recommend you to have a look at the browseable
API (http://www.freesound.org/apiv2). You'll need to be logged in Freesound to be able to use the browseable API.
Check out the :ref:`resources` page for complete information and examples.


Authentication
--------------

In order to start using APIv2 you'll need an API credential that you can request in (http://www.freesound.org/apiv2/apply).
API credentials given for APIv2 **can also be used for APIv1**.
Basic API calls can be authenticated using a typical token/key mechanism in which you'll need to add the key given with your APIv2 credential into every request you make as a ``token`` request parameter:

::

  curl "http://www.freesound.org/apiv2/search/?query=piano&token=YOUR_API_KEY"

However, there are some APIv2 resources that require the use of OAuth2 authentication.
Please, read the :ref:`authentication` docs for a complete description of both authentication methods and on how to use them.


Formats
-------

The format of the response can be specified in the request and can be
one of JSON, XML and YAML. We recommend using JSON, as this
is currently the only response format we actively test.

To specify the desired response format use a ``format`` request parameter.
Specify the desired format in lowercase letters as follows:

::

  http://www.freesound.org/apiv2/sounds/1234/?format=json
  http://www.freesound.org/apiv2/sounds/1234/?format=xml
  http://www.freesound.org/apiv2/sounds/1234/?format=yaml



More help
---------

If you need more help after reading these documents or want to stay up to
date on any changes or future feaures of the Freesound APIv2 or if you would
like to request more features for the API, please use our google group:


- http://groups.google.com/group/freesound-api