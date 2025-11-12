.. _resources:

Resources
<<<<<<<<<

.. contents::
    :depth: 3


Search resources
>>>>>>>>>>>>>>>>

.. warning:: When using the search resources make sure to include the ``fields`` parameter (see :ref:`sound-list-response`)
  so that you get all needed metadata for each search result in a single request. In this way you'll **avoid  having to perform
  one extra API request** to retrieve the desired metadata for each individual result.


.. _sound-search:

Search
=========================================================

::

  GET /apiv2/search/

.. note:: Note that this search endpoint replaces the deprecated ``/apiv1/search/text`` endpoint (deprecated in November 2025). 
  While the old endpoint currently redirects here, users are advised to update their integrations to call this endpoint directly.

This resource allows searching for sounds in Freesound by matching user metadata (e.g. tags, username), precomputed content-based descriptors, and other kinds of metadata.

.. _sound-search-parameters:


Parameters
-------------------------------------------

Search queries are defined using the following parameters:

=====================================  =========================  ======================
Name                                   Type                       Description
=====================================  =========================  ======================
``query``                              string                     The query! The ``query`` is the main parameter used to define a query. You can type several terms separated by spaces or phrases wrapped inside quote '"' characters. For every term, you can also use '+' and '-' modifier characters to indicate that a term is "mandatory" or "prohibited" (by default, terms are considered to be "mandatory"). For example, in a query such as ``query=term_a -term_b``, sounds including ``term_b`` will not match the search criteria. The query does a weighted search over some sound properties including sound tags, the sound name, its description, pack name and the sound id. Therefore, searching for ``query=123`` will find you sounds with id 1234, sounds that have 1234 in the description, in the tags, etc. You'll find some examples below. Using an empty query (``query=`` or ``query=""``) will return all Freesound sounds.
:ref:`filter <search-filter>`          string                     Allows filtering query results. See below for more information.
:ref:`sort <search-sort>`              string                     Indicates how query results should be sorted. See below for a list of the sorting options. By default ``sort=score``.
:ref:`similar_to <search-similar>`     integer or array[float]   Allows finding sounds similar to a given sound. You can pass the ID of a sound (integer) or a similarity vector (array of floats separated by commas) and the results will be sorted by their similarity to this sound.
:ref:`similar_space <search-similar>`  string                     Indicates the similarity space used when performing similarity search. If not defined, the default similarity space is used.
``group_by_pack``                      bool (yes=1, no=0)         This parameter represents a boolean option to indicate whether to collapse results belonging to sounds of the same pack into single entries in the results list. If ``group_by_pack=1`` and search results contain more than one sound that belongs to the same pack, only one sound for each distinct pack is returned (sounds with no packs are returned as well). However, the returned sound will feature two extra properties to access these other sounds omitted from the results list: ``n_from_same_pack``: indicates how many other results belong to the same pack (and have not been returned) ``more_from_same_pack``: uri pointing to the list of omitted sound results of the same pack (also including the result which has already been returned). See examples below. By default ``group_by_pack=0``.
:ref:`weights <search-weights>`        string                     Allows definition of custom weights when matching queries with sound metadata fields. You should most likely never use that :)
:ref:`fields <search-fields>`          strings (comma separated)  Indicates which sound properties should be included in every sound of the response. Sound properties can be any of those listed in :ref:`sound-instance-response` (plus an additional field ``score`` which returns a matching score added by the search engine), and must be separated by commas. By default ``fields=id,name,tags,username,license``. **Use this parameter to optimize request time by only requesting the information you really need.**
``page``                               string                     Query results are paginated, this parameter indicates what page should be returned. By default ``page=1``.
``page_size``                          string                     Indicates the number of sounds per page to include in the result. By default ``page_size=15``, and the maximum is ``page_size=150``. Note that with bigger ``page_size``, more data will need to be transferred.
=====================================  =========================  ======================


.. _search-filter:

The 'filter' parameter
~~~~~

Search results can be filtered by specifying a series of properties that sounds should match.
In other words, using the ``filter`` parameter you can specify the value that certain sound fields should have in order to be considered valid search results.
Filters are defined with a syntax like ``filter=filtername:value filtername:value`` (that is the Solr filter syntax).
Use double quotes for multi-word queries (``filter=filtername:"val ue"``).
Filter names can be any of the following:

======================  =============  ====================================================
Filter name             Type           Description
======================  =============  ====================================================
``id``                  integer        Sound ID on Freesound.
``username``            string         Username of the sound uploader (not tokenized).
``created``             date           Date in which the sound was added to Freesound (see date example filters below).
``original_filename``   string         Name given to the sound (tokenized).
``category``            string         Category name (top-level category) from the `Broad Sound Taxonomy <https://freesound.org/help/faq/#the-broad-sound-taxonomy>`_ (e.g. "Instrument samples"). 
``subcategory``         string         Subategory name (second-level category) from the `Broad Sound Taxonomy <https://freesound.org/help/faq/#the-broad-sound-taxonomy>`_ (e.g. "Piano / Keyboard instruments"). For optimal results, it is recommended to use this filter in combination with the ``category`` filter.
``tag``                 string         Tag of the sound.
``description``         string         Textual description given to the sound (tokenized).
``license``             string         Name of the Creative Commons license, one of ["Attribution", "Attribution NonCommercial", "Creative Commons 0"].
``is_remix``            boolean        Whether the sound is a remix of another Freesound sound.
``was_remixed``         boolean        Whether the sound has remixes in Freesound.
``pack``                string         Pack name (not tokenized).
``pack_tokenized``      string         Pack name (tokenized).
``is_geotagged``        boolean        Whether the sound has geotag information.
``type``                string         Original file type, one of ["wav", "aiff", "ogg", "mp3", "m4a", "flac"].
``duration``            numeric        Duration of sound in seconds.
``bitdepth``            integer        Encoding bitdepth. WARNING is not to be trusted right now.
``bitrate``             numeric        Encoding bitrate. WARNING is not to be trusted right now.
``samplerate``          integer        Samplerate.
``filesize``            integer        File size in bytes.
``channels``            integer        Number of channels in sound (mostly 1 or 2).
``md5``                 string         32-byte md5 hash of file.
``num_downloads``       integer        Number of times the sound has been downloaded.
``avg_rating``          numeric        Average rating for the sound in the range [0, 5].
``num_ratings``         integer        Number of times the sound has been rated.
``comment``             string         Textual content of the comments of a sound  (tokenized). The filter is satisfied if sound contains the filter value in at least one of its comments.
``num_comments``        integer        Number of times the sound has been commented.
======================  =============  ====================================================

Additionally, the following content-based filters can be used when narrowing down a query. 
These filters enable content-based search in Freesound using audio descriptors that mainly come from Essentia_, 
as well as from related initiatives such as the AudioCommons_ project.

.. _AudioCommons: http://www.audiocommons.org/
.. _Essentia: https://essentia.upf.edu/

========================  =======  =================================================================================================================================================================================================================================================================================================================
Filter name               Type     Description                                                                                                                                                                                                                                                                                                      
========================  =======  =================================================================================================================================================================================================================================================================================================================
amplitude_peak_ratio_     numeric  Ratio between the position of the peak in the amplitude envelope and the total envelope duration, indicating whether the maximum magnitude of the audio signal occurs early (impulsive or decrescendo) or late (crescendo).                                                                                      
beat_count_               integer  Number of beats in the audio signal, derived from the total detected beat positions and expresses a measure of rhythmic density or tempo-related activity.                                                                                                                                                       
beat_loudness_            numeric  Spectral energy measured at the beat positions of the audio signal.                                                                                                                                                                                                                                              
boominess_                numeric  Boominess of the audio signal. A boomy sound is one that conveys a sense of loudness, depth and resonance.                                                                                                                                                                                                       
bpm_                      integer  BPM value estimated by beat tracking algorithm.                                                                                                                                                                                                                                                                  
bpm_confidence_           numeric  Confidence score on how reliable the tempo (BPM) estimation is.                                                                                                                                                                                                                                                  
brightness_               numeric  Brightness of the audio signal. A bright sound is one that is clear/vibrant and/or contains significant high-pitched elements.                                                                                                                                                                                   
chord_count_              integer  Number of chords in the audio signal based on the number of detected chords by the chord_progression descriptor.                                                                                                                                                                                                 
decay_strength_           numeric  Rate at which the audio signal's energy decays (i.e. how quickly it decreases) after the initial attack. It is computed from a non-linear combination of the signal's energy and its temporal centroid (the balance point of the signal's absolute amplitude).                                                   
depth_                    numeric  Depth of the audio signal. A deep sound is one that conveys the sense of having been made far down below the surface of its source.                                                                                                                                                                              
dissonance_               numeric  Sensory dissonance of the audio signal given its spectral peaks.                                                                                                                                                                                                                                                 
duration_                 numeric  Total duration of the audio signal in seconds.                                                                                                                                                                                                                                                                   
duration_effective_       numeric  Duration of the audio signal (in seconds) during which the envelope amplitude is perceptually significant (above 40% of peak and ?90?dB), e.g. for distinguishing short/percussive from sustained sounds.                                                                                                        
dynamic_range_            numeric  Loudness range (dB, LU) of the audio signal measured using the EBU R128 standard.                                                                                                                                                                                                                                
hardness_                 numeric  Hardness of the audio signal. A hard sound is one that conveys the sense of having been made (i) by something solid, firm or rigid; or (ii) with a great deal of force.                                                                                                                                          
hpcp_crest_               numeric  Dominance of the strongest pitch class (crest) compared to the rest, computed as the ratio between the maximum HPCP value and the mean HPCP value (computed by the hpcp descriptor).                                                                                                                             
hpcp_entropy_             numeric  Uniformity of the pitch-class distribution, computed as the Shannon entropy of the HPCP (computed by the hpcp descriptor).                                                                                                                                                                                       
inharmonicity_            numeric  Deviation of spectral components from perfect harmonicity, computed as the energy-weighted divergence from their closest multiples of the fundamental frequency.                                                                                                                                                 
log_attack_time_          numeric  Log (base 10) of the attack time of the audio signal's envelope, where the attack time is defined as the time duration from when the sound becomes perceptually audible to when it reaches its maximum intensity.                                                                                                
loopable_                 boolean  Whether the audio signal is loopable, i.e. it begins and ends in a way that sounds smooth when repeated.                                                                                                                                                                                                         
loudness_                 numeric  Overall loudness (LUFS) of the audio signal measured using the EBU R128 standard.                                                                                                                                                                                                                                
note_confidence_          numeric  Confidence score on how reliable the note name/MIDI estimation is.                                                                                                                                                                                                                                               
note_midi_                integer  MIDI value corresponding to the estimated note (computed by the note_name descriptor).                                                                                                                                                                                                                           
note_name_                string   Pitch note name that includes one of the 12 western notes ["A", "A#", "B", "C", "C#", "D", "D#", "E", "F", "F#", "G", "G#"] and the octave number, e.g. "A4", "E#7". It is computed by the median of the estimated fundamental frequency.                                                                        
onset_count_              integer  Number of detected onsets in the audio signal.                                                                                                                                                                                                                                                                   
pitch_                    numeric  Mean (average) fundamental frequency derived from the audio signal, computed with the YinFFT algorithm.                                                                                                                                                                                                          
pitch_max_                numeric  Maximum fundamental frequency observed throughout the audio signal.                                                                                                                                                                                                                                              
pitch_min_                numeric  Minimum fundamental frequency observed throughout the audio signal.                                                                                                                                                                                                                                              
pitch_salience_           numeric  Pitch salience (i.e. tone sensation) given by the ratio of the highest auto correlation value of the spectrum to the non-shifted auto correlation value. Unpitched sounds and pure tones have value close to 0.                                                                                                  
pitch_var_                numeric  Variance of the fundamental frequency of the audio signal.                                                                                                                                                                                                                                                       
reverbness_               boolean  Whether the signal is reverberated or not.                                                                                                                                                                                                                                                                       
roughness_                numeric  Roughness of the audio signal. A rough sound is one that has an uneven or irregular sonic texture.                                                                                                                                                                                                               
sharpness_                numeric  Sharpness of the audio signal. A sharp sound is one that suggests it might cut if it were to take on physical form.                                                                                                                                                                                              
silence_rate_             numeric  Amount of silence in the audio signal, computed by the fraction of frames with instant power below ?30?dB.                                                                                                                                                                                                       
single_event_             boolean  Whether the audio signal contains one single audio event or more than one. This computation is based on the loudness of the signal and does not do any frequency analysis.                                                                                                                                       
spectral_centroid_        numeric  Spectral centroid of the audio signal, indicating where the "center of mass" of the spectrum is. It correlates with the perception of "brightness" of a sound, making it useful for characterizing musical timbre. It is computed as the weighted mean of the signal's frequencies, weighted by their magnitudes.
spectral_complexity_      numeric  Spectral complexity of the audio signal's spectrum, based on the number of peaks in the spectrum.                                                                                                                                                                                                                
spectral_crest_           numeric  Dominance of the strongest spectral peak (crest) compared to the rest, computed as the ratio between the maximum and mean spectral magnitudes.                                                                                                                                                                   
spectral_energy_          numeric  Energy in the spectrum of the audio signal. It represents the total magnitude of all frequency components and indicates how much power is present across the spectrum.                                                                                                                                           
spectral_entropy_         numeric  Shannon entropy in the frequency domain of the audio signal, measuring the unpredictability in the spectrum.                                                                                                                                                                                                     
spectral_flatness_        numeric  Flatness of the spectrum measured as the ratio of its geometric mean to its arithmetic mean (in dB). High values indicate a noise-like, flat spectrum with evenly distributed power, while low values indicate a tone-like, spiky spectrum with power concentrated in a few frequency bands.                     
spectral_rolloff_         numeric  Roll-off frequency of the spectrum, defined as the frequency under which some percentage (cutoff) of the total energy of the spectrum is contained. It can be used to distinguish between harmonic (below roll-off) and noisy sounds (above roll-off).                                                           
spectral_skewness_        numeric  Skewness of the spectrum given its central moments. It measures how the values of the spectrum are dispersed around the mean and is a key indicator of the distribution's shape.                                                                                                                                 
spectral_spread_          numeric  Spread (variance) of the spectrum given its central moments. It measures how the values of the spectrum are dispersed around the mean and is a key indicator of the distribution's shape.                                                                                                                        
start_time_               numeric  The moment at which sound begins in seconds, i.e. when the audio signal first rises above silence.                                                                                                                                                                                                               
temporal_centroid_        numeric  Temporal centroid of the audio signal, defined as the time point at which the temporal balancing position of the sound event energy.                                                                                                                                                                             
temporal_centroid_ratio_  numeric  Ratio of the temporal centroid to the total length of the audio signal's envelope, which shows how the sound is �balanced'. Values close to 0 indicate most of the energy is concentrated early (decrescendo or impulsive), while values close to 1 indicate energy concentrated late (crescendo).               
temporal_decrease_        numeric  Overall decrease of the audio signal's amplitude over time, computed as the linear regression coefficient.                                                                                                                                                                                                       
temporal_skewness_        numeric  Skewness of the audio signal in the time domain given its central moments. It measures how the amplitude values of the signal are dispersed around the mean and is a key indicator of the distribution's shape.                                                                                                  
temporal_spread_          numeric  Spread (variance) of the audio signal in the time domain given its central moments. It measures how the amplitude values of the signal are dispersed around the mean and is a key indicator of the distribution's shape.                                                                                         
tonality_                 string   Key (tonality) estimated by a key detection algorithm. The key name includes the root note of the scale, which is one of ["A", "A#", "B", "C", "C#", "D", "D#", "E", "F", "F#", "G", "G#"], and the scale mode, which is one of ["major", "minor"], e.g. "C minor", "F# major".                                  
tonality_confidence_      numeric  Confidence score on how reliable the key estimation is (computed by the tonality descriptor).                                                                                                                                                                                                                    
warmth_                   numeric  Warmth of the audio signal. A warm sound is one that promotes a sensation analogous to that caused by a physical increase in temperature.                                                                                                                                                                        
zero_crossing_rate_       numeric  Zero-crossing rate of the audio signal. It is the number of sign changes between consecutive samples divided by the total number of samples. Noisy signals tend to have a higher value. For monophonic tonal signals, it can be used as a primitive pitch detection algorithm.                                   
========================  =======  =================================================================================================================================================================================================================================================================================================================

.. _amplitude_peak_ratio: https://freesound.org/docs/api/analysis_docs.html#amplitude_peak_ratio
.. _beat_count: https://freesound.org/docs/api/analysis_docs.html#beat_count
.. _beat_loudness: https://freesound.org/docs/api/analysis_docs.html#beat_loudness
.. _boominess: https://freesound.org/docs/api/analysis_docs.html#boominess
.. _bpm: https://freesound.org/docs/api/analysis_docs.html#bpm
.. _bpm_confidence: https://freesound.org/docs/api/analysis_docs.html#bpm_confidence
.. _brightness: https://freesound.org/docs/api/analysis_docs.html#brightness
.. _chord_count: https://freesound.org/docs/api/analysis_docs.html#chord_count
.. _decay_strength: https://freesound.org/docs/api/analysis_docs.html#decay_strength
.. _depth: https://freesound.org/docs/api/analysis_docs.html#depth
.. _dissonance: https://freesound.org/docs/api/analysis_docs.html#dissonance
.. _duration: https://freesound.org/docs/api/analysis_docs.html#duration
.. _duration_effective: https://freesound.org/docs/api/analysis_docs.html#duration_effective
.. _dynamic_range: https://freesound.org/docs/api/analysis_docs.html#dynamic_range
.. _hardness: https://freesound.org/docs/api/analysis_docs.html#hardness
.. _hpcp_crest: https://freesound.org/docs/api/analysis_docs.html#hpcp_crest
.. _hpcp_entropy: https://freesound.org/docs/api/analysis_docs.html#hpcp_entropy
.. _inharmonicity: https://freesound.org/docs/api/analysis_docs.html#inharmonicity
.. _log_attack_time: https://freesound.org/docs/api/analysis_docs.html#log_attack_time
.. _loopable: https://freesound.org/docs/api/analysis_docs.html#loopable
.. _loudness: https://freesound.org/docs/api/analysis_docs.html#loudness
.. _note_confidence: https://freesound.org/docs/api/analysis_docs.html#note_confidence
.. _note_midi: https://freesound.org/docs/api/analysis_docs.html#note_midi
.. _note_name: https://freesound.org/docs/api/analysis_docs.html#note_name
.. _onset_count: https://freesound.org/docs/api/analysis_docs.html#onset_count
.. _pitch: https://freesound.org/docs/api/analysis_docs.html#pitch
.. _pitch_max: https://freesound.org/docs/api/analysis_docs.html#pitch_max
.. _pitch_min: https://freesound.org/docs/api/analysis_docs.html#pitch_min
.. _pitch_salience: https://freesound.org/docs/api/analysis_docs.html#pitch_salience
.. _pitch_var: https://freesound.org/docs/api/analysis_docs.html#pitch_var
.. _reverbness: https://freesound.org/docs/api/analysis_docs.html#reverbness
.. _roughness: https://freesound.org/docs/api/analysis_docs.html#roughness
.. _sharpness: https://freesound.org/docs/api/analysis_docs.html#sharpness
.. _silence_rate: https://freesound.org/docs/api/analysis_docs.html#silence_rate
.. _single_event: https://freesound.org/docs/api/analysis_docs.html#single_event
.. _spectral_centroid: https://freesound.org/docs/api/analysis_docs.html#spectral_centroid
.. _spectral_complexity: https://freesound.org/docs/api/analysis_docs.html#spectral_complexity
.. _spectral_crest: https://freesound.org/docs/api/analysis_docs.html#spectral_crest
.. _spectral_energy: https://freesound.org/docs/api/analysis_docs.html#spectral_energy
.. _spectral_entropy: https://freesound.org/docs/api/analysis_docs.html#spectral_entropy
.. _spectral_flatness: https://freesound.org/docs/api/analysis_docs.html#spectral_flatness
.. _spectral_rolloff: https://freesound.org/docs/api/analysis_docs.html#spectral_rolloff
.. _spectral_skewness: https://freesound.org/docs/api/analysis_docs.html#spectral_skewness
.. _spectral_spread: https://freesound.org/docs/api/analysis_docs.html#spectral_spread
.. _start_time: https://freesound.org/docs/api/analysis_docs.html#start_time
.. _temporal_centroid: https://freesound.org/docs/api/analysis_docs.html#temporal_centroid
.. _temporal_centroid_ratio: https://freesound.org/docs/api/analysis_docs.html#temporal_centroid_ratio
.. _temporal_decrease: https://freesound.org/docs/api/analysis_docs.html#temporal_decrease
.. _temporal_skewness: https://freesound.org/docs/api/analysis_docs.html#temporal_skewness
.. _temporal_spread: https://freesound.org/docs/api/analysis_docs.html#temporal_spread
.. _tonality: https://freesound.org/docs/api/analysis_docs.html#tonality
.. _tonality_confidence: https://freesound.org/docs/api/analysis_docs.html#tonality_confidence
.. _warmth: https://freesound.org/docs/api/analysis_docs.html#warmth
.. _zero_crossing_rate: https://freesound.org/docs/api/analysis_docs.html#zero_crossing_rate


For numeric or integer filters, a **range can also be specified** using the following syntax (the "TO" must be uppercase!)::

  filter=filtername:[start TO end]
  filter=filtername:[* TO end]
  filter=filtername:[start to \*]  (NOT valid)

Note: It is recommended to use ranges when dealing with numeric values (which may be floats), as is common for many content-based filters, 
because matching an exact value is rare.

Dates can also have ranges and math expressions (the "TO" must still be uppercase!)::

  filter=created:[* TO NOW]
  filter=created:[1976-03-06T23:59:59.999Z TO *]
  filter=created:[1995-12-31T23:59:59.999Z TO 2007-03-06T00:00:00Z]
  filter=created:[NOW-1YEAR/DAY TO NOW/DAY+1DAY]
  filter=created:[1976-03-06T23:59:59.999Z TO 1976-03-06T23:59:59.999Z+1YEAR]
  filter=created:[1976-03-06T23:59:59.999Z/YEAR TO 1976-03-06T23:59:59.999Z]

Simple logic operators can also be used in filters::

  filter=type:(wav OR aiff)
  filter=description:(piano AND note)

See below for some :ref:`sound-search-examples` on different types of filters! 

**Filter queries using geotagging data**

Search also supports filtering query results using geotagging data.
For example, you can retrieve sounds that were recorded near a particular location or filter the results of a query to those sounds recorded in a geospatial area.
Note that not all sounds in Freesound are geotagged, and the results of such queries will only include geotagged sounds.
In general, you can define geotagging queries in two ways:

 1) By specifying a point in space and a maximum distance: this way lets you specify a latitude and longitude target point,
 and a maximum distance (in km) from that point. Query results will only include those points contained in the area.
 You can use the ``filter`` parameter of a standard query to specify latitude, longitude and maximum distance using the
 following syntax::

  filter={!geofilt sfield=geotag pt=<LATITUDE>,<LONGITUDE> d=<MAX_DISTANCE_IN_KM>}

 2) By specifying an arbitrary rectangle in space: this way lets you define a rectangle in space by specifying a
 minimum latitude and longitude, and a maximum latitude and longitude.
 Query results will only include those points contained in the area.
 You can use the ``filter`` parameter of a standard query to specify minimum and maximum latitude and longitude using the
 following syntax::

  filter=geotag:["<MINIMUM_LATITUDE>, <MINIMUM_LONGITUDE>" TO "<MAXIMUM_LONGITUDE> <MAXIMUM_LATITUDE>"]

 Minimum and maximum latitude and longitude define the lower left and upper right corners of the rectangle as shown below.
 Besides ``Intersects``, you can also use ``IsDisjointTo``, which will return all sounds geotagged outside the rectangle.

    .. image:: _static/geotags/geotag_normal.png
        :align: center

Please refer to the Solr documentation on spatial queries for extra information (http://wiki.apache.org/solr/SolrAdaptersForLuceneSpatial4) and check the examples below.


.. _search-sort:

The 'sort' parameter
~~~~~

The ``sort`` parameter determines how the results are sorted, and can only be one
of the following.

==============  ====================================================================
Option          Explanation
==============  ====================================================================
score           Sort by a relevance score returned by our search engine (default).
duration_desc   Sort by the duration of the sounds, longest sounds first.
duration_asc    Same as above, but shortest sounds first.
created_desc    Sort by the date of when the sound was added. newest sounds first.
created_asc	    Same as above, but oldest sounds first.
downloads_desc  Sort by the number of downloads, most downloaded sounds first.
downloads_asc   Same as above, but least downloaded sounds first.
rating_desc     Sort by the average rating given to the sounds, highest rated first.
rating_asc      Same as above, but lowest rated sounds first.
==============  ====================================================================


.. _search-similar:

The 'similar_to' and 'simiarity_space' parameters
~~~~~

These parameters allow similarity-based search in order to retrieve sounds that are acoustically, semantically, or perceptually similar to a given reference sound.
The ``similar_to`` parameter takes the ID of a sound (e.g. 1234) or a similarity vector (e.g. [1.36, 2.05, ..]) and returns results sorted by similarity to that sound. For example::

  similar_to=<SOUND_ID>&similarity_space=<SIMILARITY_SPACE_NAME>

When using a sound ID, it should be a valid Freesound ID corresponding to a sound that exists.
When using a similarity vector, it should be obtained by extracting the a feature representation for a sound corresponding to the used similarity space (see below).

The ``similarity_space`` parameter can optionally be used (in combination with ``similar_to``) to indicate which feature space should be used for computing similarity. 
Each similarity space is built using different types of descriptors, ranging from low-level acoustic characteristics to semantically informed or perceptual sound information. 
If the ``similarity_space`` parameter is not specified, the default space is used. These are the similarity spaces which are currently available:

=====================  =====================  ====================================================================
Simialrity space name  Number of dimensions   Explanation
=====================  =====================  ====================================================================
laion_clap             512                    This space is built using LAION-CLAP embeddings, which designed to capture both acoustic and semantic properties of sounds. We use L2-normed versions of the embeddings that can be extracted using the standard tools provided by LAION organisation (https://github.com/LAION-AI/CLAP). We use the ``630k-audioset-fusion-best.pt`` pre-trained model.
freesound_classic      100                    This space is built using a combination of low-level acoustic audio features extracted using the ``FreesoundExtractor`` from the Essentia audio analysis library (https://essentia.upf.edu). We currently don't provide code to extract these features from arbitrary audio, but we might do that in the future.
=====================  =====================  ====================================================================


.. _search-weights:

The 'weights' parameter
~~~~~

The ``weights`` parameter can be used to define custom weights when matching queries with sound metadata fields. You can use any of the field names listed above 
(although some might not make sense when preparing a query) and specify integer weights for each field using the following syntax::

  weights=field_name:integer_weight,field_name2:integer_weight2

If the format is not correct, custom weights will not be applied. 
The default weights are something like ``id:4,tag:4,description:3,original_filename:2,username:2,pack:2``.


.. _search-fields:

The 'fields' parameter
~~~~~

The ``fields`` parameter defines the sound information that is returned for every sound in the results.
If ``fields``  is not specified, a minimal set of information for every sound result is returned by default.
This includes the ID of the sound, the name and tags of the sound, the username of the sound uploader, and the license,
i.e. by default ``fields=id,name,tags,username,license``.
When ``fields`` is specified, the default fields are not included and must be explicitly defined if needed.
For example, if ``fields=name,score,avg_rating,license`` is used, results will include sound name, search engine score relative to the query, 
average rating, and license for every returned sound.


.. _sound-list-response:

Response (sound list)
---------------------

Search resource returns a *sound list response*. Sound list responses have the following structure:

::

  {
    "count": <total number of results>,
    "next": <link to the next page of results (null if none)>,
    "results": [
        <sound result #1 info>,
        <sound result #2 info>,
        ...
        <sound result #page_size info>
    ],
    "previous": <link to the previous page of results (null if none)>
  }

You can use the parameters ``fields``, ``page``, and ``page_size`` some of the contents of the sound list response.


.. _sound-search-examples:

Examples
--------

{{examples_Search}}


.. _sound-content-search:

Content Search (deprecated)
=========================================================

::

  GET /apiv2/search/content/
  POST /apiv2/search/content/

This resource allows searching sounds in Freesound based on their content descriptors.

.. warning:: As of December 2023, this resource is deprecated and will be removed in the comming months. Similar functionality
  will be achievable using the :ref:`sound-search` resource. Documentation about how to do this will be added in due time
  but in the meantime, please contact us if you need help with this.

.. _sound-content-search-parameters:

Parameters (content search parameters)
----------------------------------------------

Content search queries are defined using the following request parameters:

=========================  =========================  ======================
Name                       Type                       Description
=========================  =========================  ======================
``target``                 string or numeric           This parameter defines a target based on content-based descriptors to sort the search results. It can be set as a number of descriptor name and value pairs, or as a sound id. See below.
``analysis_file``          file                       **Experimental** - Alternatively, targets can be specified by uploading a file with the output of the Essentia Freesound Extractor analysis of any sound that you analyzed locally (see below). This parameter overrides ``target``, and requires the use of POST method.
``descriptors_filter``     string                     This parameter allows filtering query results by values of the content-based descriptors. See below for more information.
=========================  =========================  ======================

**The 'target' and 'analysis_file' parameters**

The ``target`` parameter can be used to specify a content-based sorting of your search results.
Using ``target`` you can sort the query results so that the first results will be the sounds featuring the most similar descriptors to the given target.
To specify a target you must use a syntax like ``target=descriptor_name:value``.
You can also set multiple descriptor/value pairs in a target separating them with spaces (``target=descriptor_name:value descriptor_name:value``).
Descriptor names must be chosen from those listed in :ref:`available-descriptors`. 
Only numerical descriptors are allowed.
Multidimensional descriptors with fixed-length (that always have the same number of dimensions) are allowed too (see below).
Consider the following two ``target`` examples::

  (A) target=lowlevel.pitch.mean:220
  (B) target=lowlevel.pitch.mean:220 lowlevel.pitch.var:0

Example A will sort the query results so that the first results will have a mean pitch as close to 220Hz as possible.
Example B will sort the query results so that the first results will have a mean pitch as close to 220Hz as possible and a pitch variance as close as possible to 0.
In that case example B will promote sounds that have a steady pitch close to 220Hz.

Multidimensional descriptors can also be used in the ``target`` parameter::

  target=sfx.tristimulus.mean:0,1,0

Alternatively, ``target`` can also be set to point to a Freesound sound.
In that case the descriptors of the sound will be used as the target for the query, therefore query results will be sorted according to their similarity to the targeted sound.
To set a sound as a target of the query you must use the sound id. For example, to use sound with id 1234 as target::

  target=1234


There is even another way to specify a target for the query, which is by uploading an analysis file generated using the Essentia Freesound Extractor.
For doing that you will need to download and compile Essentia (we recommend using release 2.0.1), an open source feature extraction library developed at the Music Technology Group (https://github.com/mtg/essentia/tree/2.0.1),
and use the 'streaming_extractor_freesound' example to analyze any sound you have in your local computer.
As a result, the extractor will create a JSON file that you can use as target in your Freesound API content search queries.
To use this file as target you will need to use the POST method (instead of GET) and attach the file as an ``analysis_file`` POST parameter (see example below).
Setting the target as an ``analysis_file`` allows you to to find sounds in Freesound that are similar to any other sound that you have in your local computer and that it is not part of Freesound.
When using ``analysis_file``, the contents of ``target`` are ignored. Note that **this feature is experimental**. Some users reported not being able to generate compatible analysis files.

Note that if ``target`` (or ``analysis_file``) is not used in combination with ``descriptors_filter``, the results of the query will
include all sounds from Freesound indexed in the similarity server, sorted by similarity to the target.


**The 'descriptors_filter' parameter**

The ``descriptors_filter`` parameter is used to restrict the query results to those sounds whose content descriptor values match with the defined filter.
To define ``descriptors_filter`` parameter you can use the same syntax as for the normal ``filter`` parameter, including numeric ranges and simple logic operators.
For example, ``descriptors_filter=lowlevel.pitch.mean:220`` will only return sounds that have an EXACT pitch mean of 220hz.
Note that this would probably return no results as a sound will rarely have that exact pitch (might be very close like 219.999 or 220.000001 but not exactly 220).
For this reason, in general it might be better to indicate ``descriptors_filter`` using ranges.
Descriptor names must be chosen from those listed in :ref:`available-descriptors`.
Note that most of the descriptors provide several statistics (var, mean, min, max...). In that case, the descriptor name must include also the desired statistic (see examples below).
Non fixed-length descriptors are not allowed.
Some examples of ``descriptors_filter`` for numerical descriptors::

  descriptors_filter=lowlevel.pitch.mean:[219.9 TO 220.1]
  descriptors_filter=lowlevel.pitch.mean:[219.9 TO 220.1] AND lowlevel.pitch_salience.mean:[0.6 TO *]
  descriptors_filter=lowlevel.mfcc.mean[0]:[-1124 TO -1121]
  descriptors_filter=lowlevel.mfcc.mean[1]:[17 TO 20] AND lowlevel.mfcc.mean[4]:[0 TO 20]

Note how in the last two examples the filter operates in a particular dimension of a multidimensional descriptor (with dimension index starting at 0).

``descriptors_filter`` can also be defined using non numerical descriptors such as 'tonal.key_key' or 'tonal.key_scale'.
In that case, the value must be enclosed in double quotes '"', and the character '#' (for example for an A# key) must be indicated with the string 'sharp'.
Non numerical descriptors can not be indicated using ranges.
For example::

  descriptors_filter=tonal.key_key:"Asharp"
  descriptors_filter=tonal.key_scale:"major"
  descriptors_filter=(tonal.key_key:"C" AND tonal.key_scale:"major") OR (tonal.key_key:"A" AND tonal.key_scale:"minor")

You can combine both numerical and non numerical descriptors as well::

  descriptors_filter=tonal.key_key:"C" tonal.key_scale="major" tonal.key_strength:[0.8 TO *]


Response
--------

The Content Search resource returns a sound list just like :ref:`sound-list-response`.
The same extra request parameters apply (``page``, ``page_size``, ``fields``, ``descriptors`` and ``normalized``).


Examples
--------

{{examples_ContentSearch}}


.. _sound-combined-search:

Combined Search (deprecated)
=========================================================

::

  GET /apiv2/search/combined/
  POST /apiv2/search/combined/

This resource is a combination of :ref:`sound-search` and :ref:`sound-content-search`, and allows searching sounds in Freesound based on their tags, metadata and content-based descriptors.

.. warning:: As of December 2023, this resource is deprecated and will be removed in the comming months. Similar functionality
  will be achievable using the :ref:`sound-search` resource. Documentation about how to do this will be added in due time
  but in the meantime, please contact us if you need help with this.

Parameters
------------------

Combined Search request parameters can include any of the parameters from text-based search queries (``query``, ``filter`` and ``sort``, :ref:`sound-search-parameters`)
and content-based search queries (``target``, ``analysis_file`` and ``descriptors_filter`` and, :ref:`sound-content-search-parameters`).
Note that ``group_by_pack`` **is not** available in combined search queries.

In Combined Search, queries can be defined both like a standard textual query or as a target of content-descriptors, and
query results can be filtered by values of sounds' metadata and sounds' content-descriptors... all at once!

To perform a Combined Search query you must at least specify a ``query`` or a ``target`` parameter (as you would do in text-based and content-based searches respectively),
and at least one text-based or content-based filter (``filter`` and ``descriptors_filter``).
Request parameters ``query`` and ``target`` can not be used at the same time, but ``filter`` and ``descriptors_filter`` can both be present in a single Combined Search query.
In any case, you must always use at least one text-based search request parameter and one content-based search request parameter.
Note that ``sort`` parameter must always be accompanied by a ``query`` or ``filter`` parameter (or both), otherwise it is ignored.
``sort`` parameter will also be ignored if parameter ``target`` (or ``analysis_file``) is present in the query.

Combined Search requests might **require significant computational resources** on our servers depending on the particular
query that is made. Therefore, responses might take longer than usual. Fortunately, response times can vary a lot
with some small modifications in the query, and this is in your hands ;).
As a general rule, we recommend not to use the text-search parameter ``query``, and instead define metadata stuff in a ``filter``.
For example, instead of setting the parameter ``query=loop``, try filtering results to sounds that have the tag loop (``filter=tag:loop``).
Furthermore, you can try narrowing down your filter or filters (``filter`` and ``descriptors_filter``) and possibly make the queries faster.
Best response times are normally obtained by specifying a content-based ``target`` in combination with text-based and
content-based filters (``filter`` and ``descriptors_filter``).


Response
--------

The Combined Search resource **returns a variation** of the standard sound list response :ref:`sound-list-response`.
Combined Search responses are dictionaries with the following structure:

::

  {
    "results": [
        <sound result #1 info>,
        <sound result #2 info>,
        ...
    ],
    "more": <link to get more results (null if there are no more results)>,
  }

The ``results`` field will include a list of sounds just like in the normal sound list response.
The length of this list can be defined using the ``page_size`` request parameter like in normal sound list responses.
However, Combined Search responses **do not guarantee** that the number of elements inside ``results`` will be equal to
the number specified in ``page_size``. In some cases, you might find less results, so **you should verify the length of the list**.

Furthermore, instead of the ``next`` and ``previous`` links to navigate among results, Combined Search responses
only offer a ``more`` link that you can use to obtain more results. You can think of the ``more`` link as a
rough equivalent to ``next``, but it does not work by indicating page numbers as in normal sound list responses.

Also, note that ``count`` field is not present in the Combined Search response, therefore you do not know in advance the total
amount of results that a query can return.

Finally, Combined Search responses does allow you to use the ``fields``, ``descriptors`` and ``normalized``
parameters just like you would do in standard sound list responses.


Examples
--------

{{examples_CombinedSearch}}


Sound resources
>>>>>>>>>>>>>>>

.. _sound-sound:

Sound Instance
=========================================================

::

  GET /apiv2/sounds/<sound_id>/

This resource allows the retrieval of detailed information about a sound.

.. warning:: If you're using this resource to get metadata for each individual result returned **after a search request**, try
  instead to include the ``fields`` parameter in your search request (see :ref:`sound-list-response`). This will allow
  you to specify which metadata is to be returned for each search result, and **remove the need of making an extra query
  for each individual result**.


.. _sound-instance-response:


Response (sound instance)
-------------------------

The Sound Instance response is a dictionary including the following properties/fields:

==============================  ================  ====================================================================================
Name                            Type              Description
==============================  ================  ====================================================================================
``id``                          numeric           The sound's unique identifier.
``url``                         URI               The URI for this sound on the Freesound website.
``name``                        string            The name user gave to the sound.
``tags``                        array[string]     An array of tags the user gave to the sound.
``description``                 string            The description the user gave to the sound.
``category``                    array[string]     A two-element array containing the sound's category and subcategory names from the `Broad Sound Taxonomy <https://freesound.org/help/faq/#the-broad-sound-taxonomy>`_. Note that categories are filled-out by an algorithm if not provided by the original author of the sound.
``category_code``               string            The category ID from the `Broad Sound Taxonomy <https://freesound.org/help/faq/#the-broad-sound-taxonomy>`_ (e.g. "fx-a", with the prefix indicating the category and the suffix indicating the subcategory). Note that categories are filled-out by an algorithm if not provided by the original author of the sound.
``category_is_user_provided``   boolean           Whether the ``category`` (and ``category_code``) were provided by the author of the sound or assigned automatically by an algorithm.
``geotag``                      string            Latitude and longitude of the geotag separated by spaces (e.g. "41.0082325664 28.9731252193", only for sounds that have been geotagged).
``created``                     string            The date when the sound was uploaded (e.g. "2014-04-16T20:07:11.145").
``license``                     string            The license under which the sound is available to you.
``type``                        string            The type of sound (wav, aif, aiff, mp3, m4a or flac).
``channels``                    numeric           The number of channels.
``filesize``                    numeric           The size of the file in bytes.
``bitrate``                     numeric           The bit rate of the sound in kbps.
``bitdepth``                    numeric           The bit depth of the sound.
``duration``                    numeric           The duration of the sound in seconds.
``samplerate``                  numeric           The samplerate of the sound.
``username``                    string            The username of the uploader of the sound.
``pack``                        URI               If the sound is part of a pack, this URI points to that pack's API resource.
``download``                    URI               The URI for retrieving the original sound.
``bookmark``                    URI               The URI for bookmarking the sound.
``previews``                    object            Dictionary containing the URIs for mp3 and ogg versions of the sound. The dictionary includes the fields ``preview-hq-mp3`` and ``preview-lq-mp3`` (for ~128kbps quality and ~64kbps quality mp3 respectively), and ``preview-hq-ogg`` and ``preview-lq-ogg`` (for ~192kbps quality and ~80kbps quality ogg respectively).
``images``                      object            Dictionary including the URIs for spectrogram and waveform visualizations of the sound. The dictionary includes the fields ``waveform_l`` and ``waveform_m`` (for large and medium waveform images respectively), and ``spectral_l`` and ``spectral_m`` (for large and medium spectrogram images respectively).
``num_downloads``               numeric           The number of times the sound was downloaded.
``avg_rating``                  numeric           The average rating of the sound.
``num_ratings``                 numeric           The number of times the sound was rated.
``rate``                        URI               The URI for rating the sound.
``comments``                    URI               The URI of a paginated list of the comments of the sound.
``num_comments``                numeric           The number of comments.
``comment``                     URI               The URI to comment the sound.
``similar_sounds``              URI               URI pointing to the :ref:`similar-sounds` resource (to get a list of similar sounds).
``analysis_files``              URIs              List of URIs for retrieving files with analysis information for each frame of the sound (see :ref:`analysis-docs`).
==============================  ================  ====================================================================================

The ``fields`` parameter can be used to restrict or expand the set of fields returned in the response. 
By default, all metadata fields are returned except for descriptors.
To return information about specific content-based descriptors, their names can be added to ``fields`` (e.g. ``fields=mfcc,bpm``).
Descriptor names can be any of those listed in :ref:`available-descriptors`.
Note that when ``fields`` is explicitly defined, the default fields are not included automatically and all desired fields must be listed explicitly.


Examples
--------

{{examples_SoundInstance}}


.. _sound-analysis:

Sound Analysis
=========================================================

::

  GET /apiv2/sounds/<sound_id>/analysis/

This resource allows the retrieval of audio analysis information of a sound.
This includes content-based descriptors and similarity vectors for the available similarity spaces.
Although content-based descriptors can also be retrieved using the ``fields`` parameter in any API resource that returns sound lists,
using the Sound Analysis resource you can retrieve **all sound descriptors** at once without filtering options. 
You can use do the :ref:`sound-sound` resource if filtering is needed.


Response
--------

The response to a Sound Analysis request is a dictionary with the values of all content-based descriptors listed in :ref:`analysis-docs`.
That dictionary can be filtered using an extra ``fields`` parameter which should include a list of comma separated descriptor names 
chosen from those listed in :ref:`available-descriptors` (e.g. ``fields=mfcc,bpm``).


Examples
--------

{{examples_SoundAnalysis}}


.. _similar-sounds:

Similar Sounds
=========================================================

::

  GET /apiv2/sounds/<sound_id>/similar/

This resource allows the retrieval of sounds similar to the given sound target.


Parameters
------------------

Essentially, the Similar Sounds resource is like the parameter ``similar_to`` in the :ref:`sound-search` resource, but with the sound ID indicated in the URI.
You can optionally define the following parameters: 

======================  =========================  ======================
Name                    Type                       Description
======================  =========================  ======================
``similarity_space``    string                     Indicates the similarity space used when performing similarity search. If not defined, the default similarity space is used.
``fields``              strings (comma separated)  Indicates which sound properties should be included in every sound of the response. Sound properties can be any of those listed in :ref:`sound-instance-response` (plus an additional field ``score`` which returns a matching score added by the search engine), and must be separated by commas. By default ``fields=id,name,tags,username,license``. **Use this parameter to optimize request time by only requesting the information you really need.**
``page``                string                     Query results are paginated, this parameter indicates what page should be returned. By default ``page=1``.
``page_size``           string                     Indicates the number of sounds per page to include in the result. By default ``page_size=15``, and the maximum is ``page_size=150``. Note that with bigger ``page_size``, more data will need to be transferred.
======================  =========================  ======================


Response
--------

Similar Sounds resource returns a sound list just like :ref:`sound-list-response`.
The same extra parameters apply (``page``, ``page_size``, ``fields``).


Examples
--------

{{examples_SimilarSounds}}


Sound Comments
=========================================================

::

  GET /apiv2/sounds/<sound_id>/comments/

This resource allows the retrieval of the comments of a sound.


Response
--------

Sound Comments resource returns a paginated list of the comments of a sound, with a similar structure as :ref:`sound-list-response`:

::

  {
    "count": <total number of comments>,
    "next": <link to the next page of comments (null if none)>,
    "results": [
        <most recent comment for sound_id>,
        <second most recent comment for sound_id>,
        ...
    ],
    "previous": <link to the previous page of comments (null if none)>
  }

Comments are sorted according to their creation date (recent comments in the top of the list).
Parameters ``page`` and ``page_size`` can be used just like in :ref:`sound-list-response` to deal with the pagination of the response.

Each comment entry consists of a dictionary with the following structure:

::

  {
    "username": <username of the user who made the comment>
    "comment": <the comment itself>,
    "created": <the date when the comment was made, e.g. "2014-03-15T14:06:48.022">
  }


Examples
--------

{{examples_SoundComments}}


.. _sound-download:

Download Sound (OAuth2 required)
=========================================================

::

  GET /apiv2/sounds/<sound_id>/download/

This resource allows you to download a sound in its original format/quality (the format/quality with which the sound was uploaded).
It requires :ref:`oauth-authentication`.

Examples
--------

{{examples_DownloadSound}}


.. _sound-upload:

Upload Sound (OAuth2 required)
=========================================================

::

  POST /apiv2/sounds/upload/

This resource allows you to upload an audio file into Freesound and (optionally) describe it.
If no file description is provided (see below), only the audio file will be uploaded and you will need to describe it later using the :ref:`sound-describe` resource.
If the file description is also provided, the uploaded file will be ready for the processing and moderation stage.
A list of uploaded files pending description, processing or moderation can be obtained using the :ref:`sound-pending-uploads` resource.

The author of the uploaded sound will be the user authenticated via OAuth2, therefore this method requires :ref:`oauth-authentication`.


Parameters
------------------

The uploaded audio file must be attached to the request as an ``audiofile`` POST parameter.
Supported file formats include .wav, .aif, .flac, .ogg and .mp3.

Additionally, the request can include the following POST parameters to provide a description for the file:

====================  ================  ====================================================================================
Name                  Type              Description
====================  ================  ====================================================================================
``name``              string            (OPTIONAL) The name that will be given to the sound. If not provided, filename will be used.
``bst_category``      string            The ID of a category to be assigned to the sound. Must be one of the subcategory IDs from the `Broad Sound Taxonomy <https://freesound.org/help/faq/#the-broad-sound-taxonomy>`_.
``tags``              string            The tags that will be assigned to the sound. Separate tags with spaces and join multi-words with dashes (e.g. "tag1 tag2 tag3 cool-tag4").
``description``       string            A textual description of the sound.
``license``           string            The license of the sound. Must be either "Attribution", "Attribution NonCommercial" or "Creative Commons 0".
``pack``              string            (OPTIONAL) The name of the pack where the sound should be included. If user has created no such pack with that name, a new one will be created.
``geotag``            string            (OPTIONAL) Geotag information for the sound. Latitude, longitude and zoom values in the form lat,lon,zoom (e.g. "2.145677,3.22345,14").
====================  ================  ====================================================================================

Note that ``bst_category``, ``tags``, ``description`` and ``license`` parameters are REQUIRED when providing a description for the file, but can be omitted if no description is provided.
In other words, you can either only provide the ``audiofile`` parameter, or provide ``audiofile`` plus ``bst_category``, ``tags``, ``description``, ``license`` and any of the other optional parameters.
In the first case, a file will be uploaded but not described (you will need to describe it later), and in the second case a file will both be uploaded and described.


Response
--------

If file description was provided, on successful upload, the Upload Sound resource will return a dictionary with the following structure:

::

  {
    "detail": "Audio file successfully uploaded and described (now pending processing and moderation)",
    "id": "<sound_id for the uploaded and described sound instance>"
  }

Note that after the sound is uploaded and described, it still needs to be processed and moderated by the team of Freesound moderators.
Therefore, **accessing the Sound Instance using the returned ``id`` will lead to a 404 Not Found error until the sound is approved by the moderators**.
If some of the required fields are missing or some of the provided fields are badly formatted, a 400 Bad Request response will be returned with a ``detail`` field describing the errors.

If file description was NOT provided, on successful upload, the Upload Sound resource will return a dictionary with the following structure:

::

  {
    "detail": "Audio file successfully uploaded (<file size>, now pending description)",
    "filename": "<filename of the uploaded audio file>"
  }

In that case, you will probably want to store the content of the ``filename`` field because
it will be needed to later describe the sound using the :ref:`sound-describe` resource.
Alternatively, you can retrieve later a the filenames of uploads pending description using the :ref:`sound-pending-uploads` resource.


Examples
--------

{{examples_UploadSound}}


.. _sound-describe:

Describe Sound (OAuth2 required)
=========================================================

::

  POST /apiv2/sounds/describe/

This resource allows you to describe a previously uploaded audio file that has not yet been described.
This method requires :ref:`oauth-authentication`.
Note that after a sound is described, it still needs to be processed and moderated by the team of Freesound moderators, therefore it will not yet appear in Freesound.
You can obtain a list of sounds uploaded and described by the user logged in using OAuth2 but still pending processing and moderation using the :ref:`sound-pending-uploads` resource.


Parameters
------------------

A request to the Describe Sound resource must include the following POST parameters:

====================  ================  ====================================================================================
Name                  Type              Description
====================  ================  ====================================================================================
``upload_filename``   string            The filename of the sound to describe. Must match with one of the filenames returned in :ref:`sound-pending-uploads` resource.
``name``              string            (OPTIONAL) The name that will be given to the sound. If not provided, filename will be used.
``bst_category``      string            The ID of a category to be assigned to the sound. Must be one of the subcategory IDs from the `Broad Sound Taxonomy <https://freesound.org/help/faq/#the-broad-sound-taxonomy>`_.
``tags``              string            The tags that will be assigned to the sound. Separate tags with spaces and join multi-words with dashes (e.g. "tag1 tag2 tag3 cool-tag4").
``description``       string            A textual description of the sound.
``license``           string            The license of the sound. Must be either "Attribution", "Attribution NonCommercial" or "Creative Commons 0".
``pack``              string            (OPTIONAL) The name of the pack where the sound should be included. If user has created no such pack with that name, a new one will be created.
``geotag``            string            (OPTIONAL) Geotag information for the sound. Latitude, longitude and zoom values in the form lat,lon,zoom (e.g. "2.145677,3.22345,14").
====================  ================  ====================================================================================


Response
--------

If the audio file is described successfully, the Describe Sound resource will return a dictionary with the following structure:

::

  {
    "detail": "Sound successfully described (now pending processing and moderation)",
    "id": "<sound_id for the uploaded and described sound instance>"
  }

Note that after the sound is described, it still needs to be processed and moderated by the team of Freesound moderators.
Therefore, **accessing the Sound Instance using the returned ``id`` will lead to a 404 Not Found error until the sound is approved by the moderators**.

If some of the required fields are missing or some of the provided fields are badly formatted, a 400 Bad Request response will be returned with a ``detail`` field describing the errors.


Examples
--------

{{examples_DescribeSound}}


.. _sound-pending-uploads:

Pending Uploads (OAuth2 required)
=========================================================

::

  GET /apiv2/sounds/pending_uploads/

This resource allows you to retrieve a list of audio files uploaded by the Freesound user logged in using OAuth2 that have not yet been described, processed or moderated.
In Freesound, when sounds are uploaded they first need to be described by their uploaders.
After the description step, sounds are automatically processed and then enter the moderation phase, where a team of human moderators either accepts or rejects the upload.
Using this resource, your application can keep track of user uploads status in Freesound.
This method requires :ref:`oauth-authentication`.


Response
--------

The Pending Uploads resource returns a dictionary with the following structure:

::

  {
    "pending_description": [
        "<filename #1>",
        "<filename #2>",
        ...
    ],
    "pending_processing": [
        <sound #1>,
        <sound #2>,
        ...
    ],
    "pending_moderation": [
        <sound #1>,
        <sound #2>,
        ...
    ],
  }

The filenames returned under "pending_description" field are used as file identifiers in the :ref:`sound-describe` resource.
Each sound entry either under "pending_processing" or "pending_moderation" fields consists of a minimal set
of information about that sound including the ``id``, ``name``, ``tags``, ``description``, ``created`` and ``license`` fields
that you would find in a :ref:`sound-instance-response`.

Sounds under "pending_processing" contain an extra ``processing_state`` field that indicates the status of the sound in the
processing step. Processing is done automatically in Freesound right after sounds are described, and it normally takes less than a minute.
Therefore, you should normally see that the list of sounds under "pending_processing" is empty. However, if there are
errors during processing, uploaded sounds will remain in this category exhibiting a ``processing_state`` equal to ``Failed``.

Sounds under "pending_moderation" also contain an extra ``images`` field containing the uris of the waveform and spectrogram
images of the sound as described in :ref:`sound-instance-response`.


Examples
--------

{{examples_PendingUploads}}


.. _sound-edit-description:

Edit Sound Description (OAuth2 required)
=========================================================

::

  POST /apiv2/sounds/<sound_id>/edit/

This resource allows you to edit the description of an already existing sound.
Note that this resource can only be used to edit descriptions of sounds created by the Freesound user logged in using OAuth2.
This method requires :ref:`oauth-authentication`.


Parameters
------------------

A request to the Edit Sound Description resource must include mostly the same POST parameters that would be included in a :ref:`sound-describe` request:

====================  ================  ====================================================================================
Name                  Type              Description
====================  ================  ====================================================================================
``name``              string            (OPTIONAL) The new name that will be given to the sound.
``bst_category``      string            (OPTIONAL) The new category ID that will be assigned to the sound. Must be one of the subcategory IDs from the `Broad Sound Taxonomy <https://freesound.org/help/faq/#the-broad-sound-taxonomy>`_.
``tags``              string            (OPTIONAL) The new tags that will be assigned to the sound. Note that if this parameter is filled, old tags will be deleted. Separate tags with spaces and join multi-words with dashes (e.g. "tag1 tag2 tag3 cool-tag4").
``description``       string            (OPTIONAL) The new textual description for the sound.
``license``           string            (OPTIONAL) The new license of the sound. Must be either "Attribution", "Attribution NonCommercial" or "Creative Commons 0".
``pack``              string            (OPTIONAL) The new name of the pack where the sound should be included. If user has created no such pack with that name, a new one will be created.
``geotag``            string            (OPTIONAL) New geotag information for the sound. Latitude, longitude and zoom values in the form lat,lon,zoom (e.g. "2.145677,3.22345,14").
====================  ================  ====================================================================================

Note that for that resource all parameters are optional.
Only the fields included in the request will be used to update the sound description
(e.g. if only ``name`` and ``tags`` are included in the request, these are the only properties that will be updated from sound description,
the others will remain unchanged).


Response
--------

If sound description is updated successfully, the Edit Sound Description resource will return a dictionary with a single ``detail`` field indicating that the sound has been successfully edited.
If some of the required fields are missing or some of the provided fields are badly formatted, a 400 Bad Request response will be returned with a ``detail`` field describing the errors.


Bookmark Sound (OAuth2 required)
=========================================================

::

  POST /apiv2/sounds/<sound_id>/bookmark/

This resource allows you to bookmark an existing sound.
The sound will be bookmarked by the Freesound user logged in using OAuth2, therefore this method requires :ref:`oauth-authentication`.


Parameters
------------------

A request to the Bookmark Sound resource can include the following POST parameters:

====================  ================  ====================================================================================
Name                  Type              Description
====================  ================  ====================================================================================
``name``              string            (OPTIONAL) The new name that will be given to the bookmark (if not specified, sound name will be used).
``category``          string            (OPTIONAL) The name of the category under the bookmark will be classified (if not specified, bookmark will have no category). If the specified category does not correspond to any bookmark category of the user, a new one will be created.
====================  ================  ====================================================================================


Response
--------

If the bookmark is successfully created, the Bookmark Sound resource will return a dictionary with a single ``detail`` field indicating that the sound has been successfully bookmarked.


Examples
--------

{{examples_BookmarkSound}}


Rate Sound (OAuth2 required)
=========================================================

::

  POST /apiv2/sounds/<sound_id>/rate/

This resource allows you to rate an existing sound.
The sound will be rated by the Freesound user logged in using OAuth2, therefore this method requires :ref:`oauth-authentication`.


Parameters
------------------

A request to the Rate Sound resource must only include a single POST parameter:

====================  ================  ====================================================================================
Name                  Type              Description
====================  ================  ====================================================================================
``rating``            integer           Integer between 0 and 5 (both included) representing the rating for the sound (i.e. 5 = maximum rating).
====================  ================  ====================================================================================


Response
--------

If the sound is successfully rated, the Rate Sound resource will return a dictionary with a single ``detail`` field indicating that the sound has been successfully rated.
If some of the required fields are missing or some of the provided fields are badly formatted, a 400 Bad Request response will be returned with a ``detail`` field describing the errors.
Note that in Freesound sounds can only be rated once by a single user. If attempting to rate a sound twice with the same user, a 409 Conflict response will be returned with a ``detail`` field indicating that user has already rated the sound.


Examples
--------

{{examples_RateSound}}


Comment Sound (OAuth2 required)
=========================================================

::

  POST /apiv2/sounds/<sound_id>/comment/

This resource allows you to post a comment to an existing sound.
The comment will appear to be made by the Freesound user logged in using OAuth2, therefore this method requires :ref:`oauth-authentication`.


Parameters
------------------

A request to the Comment Sound resource must only include a single POST parameter:

====================  ================  ====================================================================================
Name                  Type              Description
====================  ================  ====================================================================================
``comment``           string            Comment for the sound.
====================  ================  ====================================================================================


Response
--------

If the comment is successfully created, the Comment Sound resource will return a dictionary with a single ``detail`` field indicating that the sound has been successfully commented.


Examples
--------

{{examples_CommentSound}}


User resources
>>>>>>>>>>>>>>

.. _user_instance:

User Instance
=========================================================

::

  GET /apiv2/users/<username>/

This resource allows the retrieval of information about a particular Freesound user.


Response
--------

The User Instance response is a dictionary including the following properties/fields:

========================  ================  ====================================================================================
Name                      Type              Description
========================  ================  ====================================================================================
``url``                   URI               The URI for this users' profile on the Freesound website.
``username``              string            The username.
``about``                 string            The 'about' text of users' profile (if indicated).
``homepage``              URI               The URI of users' homepage outside Freesound (if indicated).
``avatar``                object            Dictionary including the URIs for the avatar of the user. The avatar is presented in three sizes ``Small``, ``Medium`` and ``Large``, which correspond to the three fields in the dictionary. If user has no avatar, this field is null.
``date_joined``           string            The date when the user joined Freesound (e.g. "2008-08-07T17:39:00").
``num_sounds``            numeric           The number of sounds uploaded by the user.
``sounds``                URI               The URI for a list of sounds by the user.
``num_packs``             numeric           The number of packs by the user.
``packs``                 URI               The URI for a list of packs by the user.
``num_posts``             numeric           The number of forum posts by the user.
``num_comments``          numeric           The number of comments that user made in other users' sounds.
========================  ================  ====================================================================================


Examples
--------

{{examples_UserInstance}}


User Sounds
=========================================================

::

  GET /apiv2/users/<username>/sounds/

This resource allows the retrieval of a list of sounds uploaded by a particular Freesound user.


Response
--------

User Sounds resource returns a sound list just like :ref:`sound-list-response`.
The same extra request parameters apply (``page``, ``page_size``, ``fields``, ``descriptors`` and ``normalized``).


Examples
--------

{{examples_UserSounds}}



User Packs
=========================================================

::

  GET /apiv2/users/<username>/packs/

This resource allows the retrieval of a list of packs created by a particular Freesound user.


Response
--------

User Packs resource returns a paginated list of the packs created by a user, with a similar structure as :ref:`sound-list-response`:

::

  {
    "count": <total number of packs>,
    "next": <link to the next page of packs (null if none)>,
    "results": [
        <most recent pack created by the user>,
        <second most recent pack created by the user>,
        ...
    ],
    "previous": <link to the previous page of packs (null if none)>
  }

Each pack entry consists of a dictionary with the same fields returned in the :ref:`pack_instance` response.
Packs are sorted according to their creation date (recent packs in the top of the list).
Parameters ``page`` and ``page_size`` can be used just like in :ref:`sound-list-response` to deal with the pagination of the response.


Examples
--------

{{examples_UserPacks}}


Pack resources
>>>>>>>>>>>>>>

.. _pack_instance:

Pack Instance
=========================================================

::

  GET /apiv2/packs/<pack_id>/

This resource allows the retrieval of information about a pack.


Response
--------

The Pack Instance response is a dictionary including the following properties/fields:

====================  ================  ====================================================================================
Name                  Type              Description
====================  ================  ====================================================================================
``id``                integer           The unique identifier of this pack.
``url``               URI               The URI for this pack on the Freesound website.
``description``       string            The description the user gave to the pack (if any).
``created``           string            The date when the pack was created (e.g. "2014-04-16T20:07:11.145").
``name``              string            The name user gave to the pack.
``username``          string            Username of the creator of the pack.
``num_sounds``        integer           The number of sounds in the pack.
``sounds``            URI               The URI for a list of sounds in the pack.
``num_downloads``     integer           The number of times this pack has been downloaded.
====================  ================  ====================================================================================


Examples
--------

{{examples_PackInstance}}


Pack Sounds
=========================================================

::

  GET /apiv2/packs/<pack_id>/sounds/

This resource allows the retrieval of the list of sounds included in a pack.


Response
--------

Pack Sounds resource returns a sound list just like :ref:`sound-list-response`.
The same extra request parameters apply (``page``, ``page_size``, ``fields``, ``descriptors`` and ``normalized``).


Examples
--------

{{examples_PackSounds}}


Download Pack (OAuth2 required)
=========================================================

::

  GET /apiv2/packs/<pack_id>/download/

This resource allows you to download all the sounds of a pack in a single zip file.
It requires :ref:`oauth-authentication`.

Examples
--------

{{examples_DownloadPack}}


Other resources
>>>>>>>>>>>>>>>

.. _me_resource:

Me (information about user authenticated using OAuth2, OAuth2 required)
=======================================================================

::

  GET /apiv2/me/

This resource returns basic information of the user that is logged in using the OAuth2 procedure.
It can be used by applications to be able to identify which Freesound user has logged in.

Response
--------

The Me resource response consists of a dictionary with all the fields present in a standard :ref:`user_instance`, plus additional ``email`` and ``unique_id`` fields that can be used by the application to uniquely identify the end user.


My Bookmark Categories
=========================================================

::

  GET /apiv2/me/bookmark_categories/

This resource allows the retrieval of a list of bookmark categories created by the logged in Freesound user.


Response
--------

User Bookmark Categories resource returns a paginated list of the bookmark categories created by a user, with a similar structure as :ref:`sound-list-response`:

::

  {
    "count": <total number of bookmark categories>,
    "next": <link to the next page of bookmark categories (null if none)>,
    "results": [
        <first bookmark category>,
        <second bookmark category>,
        ...
    ],
    "previous": <link to the previous page of bookmark categories (null if none)>
  }

Parameters ``page`` and ``page_size`` can be used just like in :ref:`sound-list-response` to deal with the pagination of the response.

Each bookmark category entry consists of a dictionary with the following structure:

::

  {
    "url": "<URI of the bookmark category in Freesound>",
    "name": "<name that the user has given to the bookmark category>",
    "num_sounds": <number of sounds under the bookmark category>,
    "sounds": "<URI to a page with the list of sounds in this bookmark category>",
  }


Examples
--------

{{examples_MeBookmarkCategories}}


My Bookmark Category Sounds
=========================================================

::

  GET /apiv2/me/bookmark_categories/<bookmark_category_id>/sounds/

This resource allows the retrieval of a list of sounds from a bookmark category created by the logged in Freesound user.


Response
--------

User Bookmark Category Sounds resource returns a sound list just like :ref:`sound-list-response`.
The same extra request parameters apply (``page``, ``page_size``, ``fields``, ``descriptors`` and ``normalized``).


Examples
--------

{{examples_MeBookmarkCategorySounds}}


.. _available-descriptors:

Available Audio Descriptors
===========================

::

  GET /apiv2/descriptors/

This resource returns information about the available audio descriptors that are extracted from Freesound sounds.
All descriptors are indexed, and most of them can be used as content-based ``filters`` in :ref:`sound-search`.

Response
--------

The response of the Available Audio Descriptors resource is a dictionary that lists descriptor names, grouped into categories according to their structure:

::

  {
    "fixed-length": {
       "one-dimensional": [
          <descriptor name>,
          <descriptor name>,
          ...
       ],
       "multi-dimensional": [
          <descriptor name>,
          <descriptor name>,
          ...
       ]
    },
    "variable-length": [
        <descriptor name>,
        <descriptor name>,
        ...
    ]
  }


Descriptors under the field ``fixed-length`` are divided among ``one-dimensional`` (descriptors that consist in a single value like spectral centroid or pitch)
and ``multi-dimensional`` (descriptors with several dimensions like mfcc or tristimulus).
Descriptors under the field ``variable-length`` may have different length depending on the sound.

The ``one-dimensional`` descriptors are those that can be used in the ``filter`` parameter of the :ref:`sound-search` resource.
The ``multi-dimensional`` and ``variable-length`` descriptors can be accessed through the ``fields`` parameter in any API resource that returns a sound list and the :ref:`sound-analysis`.

For more information check the :ref:`analysis-docs`.
