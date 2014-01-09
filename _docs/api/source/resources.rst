.. _resources:

API V2 Resources
<<<<<<<<<<<<<<<<

Search resources
>>>>>>>>>>>>>>>>

Search
======

::

  GET /apiv2/search/

This resource allows searching sounds in Freesound by matching their tags and other kinds of metadata.

Request parameters
------------------

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
``fields``              comma separated strings    text
``descirptors``         comma separated strings    text
``normalized``          bool (yes=1, no=0)         text
======================  =========================  ======================


Examples
--------

{{examples_search}}