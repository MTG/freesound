.. _resources:

Resources
<<<<<<<<<

Sounds
>>>>>>






Sound Search resource
=====================

URI
---

::

  /sounds/search

The only allowed method is GET.

GET
---

Request
'''''''

**Parameters**

=========  ======  ========  =================================
Name       Type    Required  Description
=========  ======  ========  =================================
q	   string  no        The query!
p          number  no        The page of the search result to get
f          string  no	     The filter
s	   string  no	     How to sort the results
=========  ======  ========  =================================

TODO: explain how querying works

TODO: explain how the filter works

The page (p) parameter can be used to paginate through the results.
Every page holds 15 sounds and the first page is page 1.

The sort (s) parameter determines how the results are sorted, and can only be one
of the following.

==============  ====================================================================
Option          Explanation
==============  ====================================================================
duration_desc   Sort by the duration of the sounds, longest sounds first.
duration_asc    Same as above, but shortest sounds first.
created_desc    Sort by the date of when the sound was added. newest sounds first.
created_asc	Same as above, but oldest sounds first.
downloads_desc  Sort by the number of downloads, most downloaded sounds first.
downloads_asc   Same as above, but least downloaded sounds first.
rating_desc     Sort by the average rating given to the sounds, highest rated first.
rating_asc      Same as above, but lowest rated sounds first.
==============  ====================================================================

**Curl Examples**

::

  # Get the third page with the query 'dogs', with the most downloaded sounds first.
  curl http://tabasco.upf.edu/api/sounds/search?p=3&q=dogs&s=downloads_desc
  TODO: examples of the more exotic search features

.. _sound-search-response:

Response
''''''''

**Properties**

===========  =======  ===========================================================================================
Name         Type     Description
===========  =======  ===========================================================================================
sounds       array    Array of sounds. Each sound looks like the `response format of a single sound resource`__.
previous     URI      The URI to go back one page in the search results.
next         URI      The URI to go forward one page in the search results.
===========  =======  ===========================================================================================

__ sound-get-response_

**JSON Example**

::

  {
    "sounds": [
        {
            "waveform_m": "http://tabasco.upf.edu/media/data/83/previews/83295__digifishmusic__Noisy_Miner_Chick_FeedMe_m.png", 
            "tags": [
                "bird", 
                "cheep", 
                "chick", 
                "manorina", 
                "melanocephala", 
                "miner", 
                "nousy", 
                "peep"
            ], 
            "url": "http://tabasco.upf.edu/people/digifishmusic/sounds/83295/", 
            "type": "wav", 
            "serve": "http://tabasco.upf.edu/api/sounds/83295/serve", 
            "spectral_m": "http://tabasco.upf.edu/media/data/83/previews/83295__digifishmusic__Noisy_Miner_Chick_FeedMe_m.jpg", 
            "spectral_l": "http://tabasco.upf.edu/media/data/83/previews/83295__digifishmusic__Noisy_Miner_Chick_FeedMe_l.jpg", 
            "user": {
                "username": "digifishmusic", 
                "url": "http://tabasco.upf.edu/people/digifishmusic/", 
                "ref": "http://tabasco.upf.edu/api/people/digifishmusic"
            }, 
            "original_filename": "Noisy_Miner_Chick_FeedMe.wav", 
            "base_filename_slug": "83295__digifishmusic__Noisy_Miner_Chick_FeedMe", 
            "duration": 48.548956916100003, 
            "waveform_l": "http://tabasco.upf.edu/media/data/83/previews/83295__digifishmusic__Noisy_Miner_Chick_FeedMe_l.png", 
            "preview": "http://tabasco.upf.edu/api/sounds/83295/preview", 
            "ref": "http://tabasco.upf.edu/api/sounds/83295", 
            "pack": "http://tabasco.upf.edu/api/packs/2090"
        }
	{'another_sound': 1},
	{'and_another': 1}
	],
    "previous": "http://tabasco.upf.edu/api/sounds/search?q=&p=1&f=&s=downloads_desc", 
    "next": "http://tabasco.upf.edu/api/sounds/search?q=&p=3&f=&s=downloads_desc"
  }





Sound resource
==============

URI
---

::

  /sounds/<sound_id>

The only allowed method is GET.

GET
---

A GET request to the sound resource returns all the information about the sound.

Request
'''''''

**Curl Example**

::

  curl http://tabasco.upf.edu/api/sounds/83295

.. _sound-get-response:

Response
''''''''

**Properties**

====================  =======  ====================================================================================
Name                  Type     Description
====================  =======  ====================================================================================
id                    number   The sound's unique identifier.
ref		      URI      The URI for this sound.
url		      URI      The URI for this sound on the Freesound website.
preview		      URI      The URI for retrieving the mp3 preview of the sound.
serve		      URI      The URI for retrieving the original sound.
type		      string   The type of sound (wav, aif, mp3, etc.).
duration	      number   The duration of the sound in seconds.
samplerate	      number   The samplerate of the sound.
bitdepth	      number   The bit depth of the sound.
filesize	      number   The size of the file in bytes.
bitrate		      number   The bit rate of the sound.
channels	      number   The number of channels.
original_filename     string   The name of the sound file when it was uploaded.
description	      string   The description the user gave the sound.
tags		      array    An array of tags the user gave the sound.
license		      string   The license under which the sound is available to you.
created		      string   The date of when the sound was uploaded.
num_comments	      number   The number of comments.
num_downloads	      number   The number of times the sound was downloaded.
num_ratings	      number   The number of times the sound was rated.
avg_rating	      number   The average rating of the sound.
pack		      URI      If the sound is part of a pack, this URI points to that pack's API resource.
user		      object   A dictionary with the username, url, and ref for the user that uploaded the sound.
spectral_m	      URI      A visualization of the sounds spectrum over time, jpeg file (medium).
spectral_l	      URI      A visualization of the sounds spectrum over time, jpeg file (large).
waveform_m	      URI      A visualization of the sounds waveform, png file (medium).
waveform_l	      URI      A visualization of the sounds waveform, png file (large).
====================  =======  ====================================================================================

**JSON Example**

::

  {
    "duration": 0.384172335601, 
    "samplerate": 44100.0, 
    "id": 83257, 
    "bitdepth": 16, 
    "num_comments": 0, 
    "filesize": 67928, 
    "preview": "http://tabasco.upf.edu/api/sounds/83257/preview", 
    "ref": "http://tabasco.upf.edu/api/sounds/83257", 
    "description": "kick bd drum goa goakick psy psykick kickdrum", 
    "tags": [
        "bd", 
        "drum", 
        "goa", 
        "goakick", 
        "kick", 
        "kickdrum", 
        "psy", 
        "psykick"
    ], 
    "serve": "http://tabasco.upf.edu/api/sounds/83257/serve", 
    "spectral_m": "http://tabasco.upf.edu/media/data/83/previews/83257__zgump__CLUB_KICK_0304_m.jpg", 
    "spectral_l": "http://tabasco.upf.edu/media/data/83/previews/83257__zgump__CLUB_KICK_0304_l.jpg", 
    "user": {
        "username": "zgump", 
        "url": "http://tabasco.upf.edu/people/zgump/", 
        "ref": "http://tabasco.upf.edu/api/people/zgump"
    }, 
    "bitrate": 1411, 
    "num_downloads": 0, 
    "num_ratings": 0, 
    "license": "Sampling+", 
    "created": "2009-11-12 19:58:17", 
    "url": "http://tabasco.upf.edu/people/zgump/sounds/83257/", 
    "type": "wav", 
    "avg_rating": 0.0, 
    "original_filename": "CLUB KICK 0304.wav", 
    "waveform_l": "http://tabasco.upf.edu/media/data/83/previews/83257__zgump__CLUB_KICK_0304_l.png", 
    "waveform_m": "http://tabasco.upf.edu/media/data/83/previews/83257__zgump__CLUB_KICK_0304_m.png", 
    "channels": 2, 
    "pack": "http://tabasco.upf.edu/api/packs/5467"
  }








Users
>>>>>



User resource
=============

URI
---

::

  /people/<username>

The only allowed method is GET.

GET
---

Request
'''''''

**Curl Examples**

::

  curl http://tabasco.upf.edu/api/people/Jovica
  curl http://tabasco.upf.edu/api/people/klankschap


Response
''''''''

**Properties**

====================  =======  ========================================================
Name                  Type     Description
====================  =======  ========================================================
username	      string   The user's username.
ref		      URI      The URI for this resource.
url		      URI      The profile page for the user on the Freesound website.
sounds		      URI      The API URI for this user's sound collection.
packs		      URI      The API URI for this user's pack collection.
first_name	      string   The user's first name, possibly empty.
last_name	      string   The user's last name, possibly empty.
about		      string   A small text the user wrote about himself.
home_page	      URI      The user's homepage, possibly empty.
signature	      string   The user's signature, possibly empty.
date_joined	      string   The date the user joined Freesound.
====================  =======  ========================================================


**JSON Example**

::

  {
    "username": "Jovica", 
    "first_name": "", 
    "last_name": "", 
    "packs": "http://tabasco.upf.edu/api/people/Jovica/packs", 
    "url": "http://tabasco.upf.edu/people/Jovica/", 
    "about": "Policy of use: you must state somewhere somehow (credit lines, web page, whatever) that the Freesound Project served this sounds. It is irrelevant to me whether you mention or not my authorship. Can't credit? Send me a personal message. (Thanks to dobroide for these words!)\r\n\r\nIf possible, I would also like to hear where the sounds are used, so if you can send me a link or something else, please do so. Thanks!\r\n\r\nCurrently adding LAYERS & DISTOPIA sample packs!\r\n\r\nFor some more information about me, click on the links below:\r\n<a href=\"http://www.myspace.com/jovicastorer\" rel=\"nofollow\">http://www.myspace.com/jovicastorer</a>\r\n\r\nAnd this is an experimental droney label for which I do some producing, engineering, mixing and mastering:\r\n<a href=\"http://www.plaguerecordings.com/index.htm\" rel=\"nofollow\">http://www.plaguerecordings.com/index.htm</a>\r\n\r\nCurrently me and a good friend of mine are working on a new <strong>c-o-l-o-u-r-s</strong> website. \r\n\r\nThe first release, <strong>'gekarameliseerd'</strong> by <strong>Jovica Storer</strong>, is available on:\r\n- emusic: <a href=\"http://www.emusic.com/album/Jovica-Storer-Gekarameliseerd-MP3-Download/11666781.html\" rel=\"nofollow\">http://www.emusic.com/album/Jovica-Storer-Gekarameliseerd-MP3-Download/11666781.html</a>\r\n- iTunes: <a href=\"http://itunes.apple.com/WebObjects/MZStore.woa/wa/viewAlbum?i=333466000&id;=333464878&s;=143443&uo;=6\" rel=\"nofollow\">http://itunes.apple.com/WebObjects/MZStore.woa/wa/viewAlbum?i=333466000&id;=333464878&s;=143443&uo;=6</a>\r\n- Napster: <a href=\"http://free.napster.com/view/album/index.html?id=13373722\" rel=\"nofollow\">http://free.napster.com/view/album/index.html?id=13373722</a>\r\nPlease check it out and if you want to support me, buy some tracks. Many thanks! \r\n\r\nNamaste!\r\nJovica Storer", 
    "home_page": "http://www.ampcast.com/music/25765/artist.php", 
    "signature": "Namaste!\r\nJovica Storer\r\n<a href=\"http://www.c-o-l-o-u-r-s.com\" rel=\"nofollow\">http://www.c-o-l-o-u-r-s.com</a>", 
    "sounds": "http://tabasco.upf.edu/api/people/Jovica/sounds", 
    "ref": "http://tabasco.upf.edu/api/people/Jovica", 
    "date_joined": "2005-05-07 17:49:39"
  }







User Sounds collection
======================

URI
---

::

  /people/<username>/sounds

The only allowed method is GET.

GET
---

TODO: what's this resource?

Request
'''''''

**Parameters**

=========  ======  ========  ========================================
Name       Type    Required  Description
=========  ======  ========  ========================================
p          number  no        The page of the sound collection to get.
=========  ======  ========  ========================================

**Curl Examples**

::

  curl http://tabasco.upf.edu/api/people/thanvannispen/sounds
  curl http://tabasco.upf.edu/api/people/inchadney/sounds?p=5

Response
''''''''

The response is the same as the `sound search response`__.

__ sound-search-response_





User Packs collection
=====================

URI
---

::

  /people/<username>/packs

The only allowed method is GET.

GET
---

Retrieve an array of the user's sound packs.

Request
'''''''

**Curl Examples**

::

  curl http://tabasco.upf.edu/api/people/dobroide/packs

Response
''''''''

**Properties**

The response is an array. Each item in the array has the same format as the `pack resource format`__.

__ pack-get-response_


**JSON Example**

::

  [
    {
        "description": "", 
        "created": "2009-09-28 09:50:08", 
        "url": "http://tabasco.upf.edu/people/dobroide/packs/5266/", 
        "sounds": "http://tabasco.upf.edu/api/packs/5266/sounds", 
        "num_downloads": 0, 
        "ref": "http://tabasco.upf.edu/api/packs/5266", 
        "name": "scrub"
    }, 
    {
        "description": "", 
        "created": "2009-09-20 10:55:32", 
        "url": "http://tabasco.upf.edu/people/dobroide/packs/5230/", 
        "sounds": "http://tabasco.upf.edu/api/packs/5230/sounds", 
        "num_downloads": 0, 
        "ref": "http://tabasco.upf.edu/api/packs/5230", 
        "name": "granada"
    }
  ]





Packs
>>>>>



Pack resource
=============

URI
---

::

  /packs/<pack_id>

The only allowed method is GET.

GET
---

Request
'''''''

**Curl Examples**

::

  curl http://tabasco.upf.edu/api/packs/5107

.. _pack-get-response:

Response
''''''''

**Properties**

====================  =======  ========================================================
Name                  Type     Description
====================  =======  ========================================================
ref		      URI      The URI for this resource.
url		      URI      The URL for this pack's page on the Freesound website.
sounds		      URI      The API URI for the pack's sound collection.
user		      object   A JSON object with the user's username, url, and ref.
name		      string   The pack's name.
description	      string   The pack's description.
created		      string   The date when the pack was created.
num_downloads	      number   The number of times the pack was downloaded.
====================  =======  ========================================================

**JSON Example**

::

  {
    "description": "", 
    "created": "2009-09-01 19:56:15", 
    "url": "http://tabasco.upf.edu/people/dobroide/packs/5107/", 
    "user": {
        "username": "dobroide", 
        "url": "http://tabasco.upf.edu/people/dobroide/", 
        "ref": "http://tabasco.upf.edu/api/people/dobroide"
    }, 
    "sounds": "http://tabasco.upf.edu/api/packs/5107/sounds", 
    "num_downloads": 0, 
    "ref": "http://tabasco.upf.edu/api/packs/5107", 
    "name": "Iceland"
  }




Pack Sounds collection
======================

URI
---

::

  /packs/<pack_id>/sounds

The only allowed method is GET.

GET
---

A paginated collection of the sounds in the pack.

Request
'''''''

**Parameters**

=========  ======  ========  ====================================
Name       Type    Required  Description
=========  ======  ========  ====================================
p          number  no        The page of the pack's sounds to get
=========  ======  ========  ====================================

**Curl Examples**

::

  curl http://tabasco.upf.edu/api/packs/5107/sounds

Response
''''''''

The response is the same as the `sound search response`__.

__ sound-search-response_







