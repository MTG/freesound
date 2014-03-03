Freesound API documentation
===========================

Welcome to the Freesound API docs!

With the Freesound API you can browse, search, and retrieve information
about Freesound users, packs, and the sounds themselves of course. You
can also find similar sounds to a given target (based on content analysis)
and retrieve automatically extracted features from audio files.


Important information
---------------------

We are in the process of releasing a new version of the Freesound API which we
call APIv2. APIv2 is currently deployed as a beta and might not be completely reliable.
Documentation for APIv2 is not yet complete although you will find some examples
in the APIv2 resources page and you can use the browseable api (http://www.freesound.org/apiv2)
to learn most of the stuff you will need.

The APIv2 brings many new features such as OAuth authentication, sound uploads and
improved search options. The release date for APIv2 is scheduled for May/June 2014, but
once APIv2 is released we will still maintain APIv1 for at least half a year. We will
announce all related news in our mailing list http://groups.google.com/group/freesound-api.

If you are starting a new project and do not need any of the new APIv2 functionalities,
we recommend you to use APIv1 for the moment.



Contents
--------


APIv1 docummentation:

.. toctree::
   :maxdepth: 1

   overview_apiv1.rst

.. toctree::
   :maxdepth: 3

   resources_apiv1.rst


APIv2 docummentation:

.. toctree::
   :maxdepth: 1

   overview.rst

.. toctree::
   :maxdepth: 3

   authentication.rst

.. toctree::
   :maxdepth: 3

   resources_apiv2.rst


Analysis docummentaion (for APIv1 and APIv2) :

.. toctree::
   :maxdepth: 3

   analysis_index.rst


API client libraries (for APIv1 and APIv2):

.. toctree::
   :maxdepth: 3

   client_libs.rst
