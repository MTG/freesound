Freesound API documentation
===========================

Welcome to the Freesound API docs!

With the Freesound API you can browse, search, and retrieve information
about Freesound users, packs, and the sounds themselves of course. You
can find similar sounds to a given target (based on content analysis)
and retrieve automatically extracted features from audio files, as well as perform
advanced queries combining content analysis features and other metadata (tags, etc...).
With the Freesound API, you can also upload, comment, rate and bookmark sounds!


As of June 2014, we have just released a **new version of the Freesound API, APIv2**.
The APIv2 brings many new features such as OAuth2 authentication, sound uploads and
improved search options.
Take into account that the previous api (APIv1) is **now deprecated**.
Although it will continue online until the end of 2014, we recommend everyone to port 
your existing applications to APIv2 as soon as possible.
If you have any questions, don't hesitate to post them in our 
mailing list http://groups.google.com/group/freesound-api.



What's new in APIv2
-------------------

- **Browseable api**. If you point your browser to http://www.freesound.org/apiv2 you'll notice that api repsonses are rendered in nice html and you can interactively browse the api. This will make it really easy to experiment and learn how to use it ;)

- **Sound uploads**. You can now upload sounds to Freesound using the api and keep track of the processing and moderation status of the uploaded files. Moreover, you can comment, rate, bookmark sounds and edit their descriptions.

- **Improved search**. APIv2 provides a new search resource that allows the definition of queries that combine metadata (tags, textual descriptions...) with automatically extracted audio descriptors. Furthermore, you can also include geotagging data in your queries.

- **Similar sounds based on analysis file**. With the new api, you can perform similarity search based on a target analysis file that you provide. This means that you can use the Freesound extractor of the open source audio analysis library Essentia to analyze any audio files that you have stored locally and retrieve similar sounds from Freesound.

- **Audio descriptors in search results**. Search resources, and any other resource that returns a list of sounds, now allow you to specify a list of audio descriptors that will be returned directly in the results page. This means that you won't have to make an extra request for every sound in the results page if you want to know some of its audio descriptor values.

- **Login with Freesound**. Using the OAuth2 protocol, you can implement 'Log in with' functionality using Freesound as backend.



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
