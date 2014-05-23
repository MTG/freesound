Freesound API documentation
===========================

Welcome to the Freesound API docs!

With the Freesound API you can browse, search, and retrieve information
about Freesound users, packs, and the sounds themselves of course. You
can find similar sounds to a given target (based on content analysis)
and retrieve automatically extracted features from audio files, as well as perform
advanced queries combining content analysis features and other metadata (tags, etc...).
With the Freesound API, you can also upload, comment, rate and bookmark sounds!


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


API documentation (APIv2):

.. toctree::
   :maxdepth: 1

   overview.rst

.. toctree::
   :maxdepth: 1

   terms_of_use.rst

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
