Freesound API documentation
===========================

Welcome to the Freesound API docs!

With the Freesound API you can browse, search, and retrieve information
about Freesound users, packs, and the sounds themselves of course. You
can find similar sounds to a given target (based on content analysis)
and retrieve automatically extracted features from audio files, as well as perform
advanced queries combining content analysis features and other metadata (tags, etc...).
With the Freesound API, you can also upload, comment, rate and bookmark sounds!


Usage of the Freesound API
--------------------------

The usage of the api is subject to the Freesound API terms of use (http://freesound.org/help/tos_api/).
Please read these terms and contact Freesound administrators at mtg *at* upf.edu if you have any doubts.
As general rules, please take into account the following points:

*  **You are free to use the Freesound API for non-commercial purposes only**. To use the Freesound API for commercial purposes,
   please contact Freesound administrators at mtg *at* upf.edu and we will talk about licensing options.


*  **Be fair with your usage of the Freesound API**. Do not use the api to replicate Freesound in another site or to present
   Freesound data pretending it is yours. Remember to properly credit Freesound and Freesound users in accordance to sounds'
   licenses.


*  **Do not abuse server badwidth**. Make reasoable use of the API and respect request limits. Do not register multiple
   API keys to circumvent request limitations. If your usage of the Freesound API requires more permissive limits,
   please contact Freesound administrators at mtg *at* upf.edu.


New API!
--------

We have just released a **new version of the Freesound API which we call APIv2**.
APIv2 is still in beta phase, but it is going to be officially released in mid June 2014.
The APIv2 brings many new features such as OAuth2 authentication, sound uploads and
improved search options.

After APIv2 is officially released, we will still maintain the old api (APIv1) until
the end of 2014. However, **APIv1 is now deprecated**.
We recommend everyone to port their applications to APIv2 as in 2015 it won't be working any more.
If you have any questions, don't hesitate to post them in our mailing list http://groups.google.com/group/freesound-api.


Contents of the docummentation
------------------------------


APIv2 documentation:

.. toctree::
   :maxdepth: 1

   overview.rst

.. toctree::
   :maxdepth: 2

   authentication.rst

.. toctree::
   :maxdepth: 2

   resources_apiv2.rst


Analysis documentation:

.. toctree::
   :maxdepth: 3

   analysis_index.rst


APIv1 documentation (deprecated):

.. toctree::
   :maxdepth: 1

   overview_apiv1.rst


API client libraries (for APIv1 and APIv2):

.. toctree::
   :maxdepth: 3

   client_libs.rst
