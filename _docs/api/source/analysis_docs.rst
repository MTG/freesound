 .. _analysis-docs:

Analysis Descriptor Documentation
<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<

.. contents::
    :depth: 3
    :backlinks: top


Analysis Settings
>>>>>>>>>>>>>>>>>

The analysis sample rate is 44100Hz and the audio file's channels are mixed down
to mono. For the lowlevel namespace the frame size is 2048 samples with a hop
size of 1024, while for the tonal namespace the frame size is 4096 and the hop
size 2048.


Acronyms for the statistics
>>>>>>>>>>>>>>>>>>>>>>>>>>>

Generally, the lowlevel descriptors have the statistics mean, max, min, var,
dmean, dmean2, dvar, and dvar2. These should be read as follows.

========= =====================================
Statistic
========= =====================================
mean      The arithmetic mean
max       The maximum value
min       The minimum value
var       The variance
dmean     The mean of the derivative
dmean2    The mean of the second derivative
dvar      The variance of the derivative
dvar2     The variance of the second derivative
========= =====================================


Metadata Descriptors
>>>>>>>>>>>>>>>>>>>>


metadata.audio_properties
-------------------------

::

    curl http://tabasco.upf.edu/api/sounds/<sound_id>/analysis/metadata/audio_properties


**Stats**::

    /analysis_sample_rate
    /bitrate
    /channels
    /downmix
    /equal_loudness
    /length
    /replay_gain

**Description**

Loads an audio file and outputs the samplerate and the number of channels. Supported formats are: wav, aiff, flac, ogg and mp3.


**Output**

dict. audio_properties (analysis_sample_rate, bitrate, channels, downmix, equal_loudness, length, replay_gain)


**Application**


**Quality Rating**


Stable


**References**


[1] WAV - Wikipedia, the free encyclopedia, http://en.wikipedia.org/wiki/Wav

[2] Audio Interchange File Format - Wikipedia, the free encyclopedia, http://en.wikipedia.org/wiki/Aiff

[3] Free Lossless Audio Codec - Wikipedia, the free encyclopedia, http://en.wikipedia.org/wiki/Flac

[4] Vorbis - Wikipedia, the free encyclopedia, http://en.wikipedia.org/wiki/Vorbis

[5] MP3 - Wikipedia, the free encyclopedia, http://en.wikipedia.org/wiki/Mp3



metadata.version
----------------

::

    curl http://tabasco.upf.edu/api/sounds/<sound_id>/analysis/metadata/version


**Stats**::

    /essentia

**Description**


Current version of analysis extractor


**Output**

dict. essentia (string)


**Application**





**Quality Rating**


Stable


**References**





Highlevel Descriptors
>>>>>>>>>>>>>>>>>>>>>


highlevel.acoustic
------------------

::

    curl http://tabasco.upf.edu/api/sounds/<sound_id>/analysis/highlevel/acoustic


**Stats**::

    /all
        /acoustic
        /not_acoustic
    /probability
    /value

**Description**





**Output**

dict. value (string), probability (real, 0 to 1), all (dict of classes and their probabilities)


**Application**





**Quality Rating**


Experimental


**References**





highlevel.ballroom
------------------

::

    curl http://tabasco.upf.edu/api/sounds/<sound_id>/analysis/highlevel/ballroom


**Stats**::

    /all
        /ChaChaCha
        /Jive
        /Quickstep
        /Rumba-American
        /Rumba-International
        /Rumba-Misc
        /Samba
        /Tango
        /VienneseWaltz
        /Waltz
    /probability
    /value

**Description**





**Output**

dict. value (string), probability (real, 0 to 1), all (dict of classes and their probabilities)


**Application**


Rhythm classification


**Quality Rating**


Experimental


**References**





highlevel.culture
-----------------

::

    curl http://tabasco.upf.edu/api/sounds/<sound_id>/analysis/highlevel/culture


**Stats**::

    /all
        /non_western
        /western
    /probability
    /value

**Description**





**Output**

dict. value (string), probability (real, 0 to 1), all (dict of classes and their probabilities)


**Application**


Detect the ethnic origin of a sound (western/non_western)


**Quality Rating**


Experimental


**References**





highlevel.electronic
--------------------

::

    curl http://tabasco.upf.edu/api/sounds/<sound_id>/analysis/highlevel/electronic


**Stats**::

    /all
        /electronic
        /not_electronic
    /probability
    /value

**Description**





**Output**

dict. value (string), probability (real, 0 to 1), all (dict of classes and their probabilities)


**Application**





**Quality Rating**


Experimental


**References**





highlevel.gender
----------------

::

    curl http://tabasco.upf.edu/api/sounds/<sound_id>/analysis/highlevel/gender


**Stats**::

    /all
        /female
        /male
    /probability
    /value

**Description**





**Output**

dict. value (string), probability (real, 0 to 1), all (dict of classes and their probabilities)


**Application**


Detect the presence of male or female voice


**Quality Rating**


Experimental


**References**





highlevel.genre
---------------

::

    curl http://tabasco.upf.edu/api/sounds/<sound_id>/analysis/highlevel/genre


**Stats**::

    /d
        /all
            /alternative
            /blues
            /country
            /electronic
            /hiphop
            /jazz
            /pop
            /rnb
            /rock
        /probability
        /value
    /e
        /all
            /ambient
            /dnb
            /house
            /techno
            /trance
        /probability
        /value
    /r
        /all
            /classical
            /dance
            /hiphop
            /jazz
            /pop
            /rnb
            /rock
            /speech
        /probability
        /value
    /t
        /all
            /blues
            /classical
            /country
            /disco
            /hiphop
            /jazz
            /metal
            /pop
            /reggae
            /rock
        /probability
        /value

**Description**





**Output**

dictionary of genre classifiers


**Application**


Genre classification


**Quality Rating**


Experimental


**References**





highlevel.live_studio
---------------------

::

    curl http://tabasco.upf.edu/api/sounds/<sound_id>/analysis/highlevel/live_studio


**Stats**::

    /all
        /live
        /studio
    /probability
    /value

**Description**





**Output**

dict. value (string), probability (real, 0 to 1), all (dict of classes and their probabilities)


**Application**


Detect if a recording was made in the studio or during a live performance


**Quality Rating**


Experimental


**References**





highlevel.moods
---------------

::

    curl http://tabasco.upf.edu/api/sounds/<sound_id>/analysis/highlevel/moods


**Stats**::

    /c
        /aggressive
            /all
                /aggressive
                /not_aggressive
            /probability
            /value
        /happy
            /all
                /happy
                /not_happy
            /probability
            /value
        /relaxed
            /all
                /not_relaxed
                /relaxed
            /probability
            /value
        /sad
            /all
                /not_sad
                /sad
            /probability
            /value
    /m
        /all
            /aggressive
            /cheerful
            /humorous
            /melancholic
            /passionate
        /probability
        /value

**Description**





**Output**

dictionary of mood classifiers


**Application**


Mood classification


**Quality Rating**


Experimental


**References**





highlevel.party
---------------

::

    curl http://tabasco.upf.edu/api/sounds/<sound_id>/analysis/highlevel/party


**Stats**::

    /all
        /not_party
        /party
    /probability
    /value

**Description**





**Output**

dict. value (string), probability (real, 0 to 1), all (dict of classes and their probabilities)


**Application**





**Quality Rating**


Experimental


**References**





highlevel.rhythm
----------------

::

    curl http://tabasco.upf.edu/api/sounds/<sound_id>/analysis/highlevel/rhythm


**Stats**::

    /all
        /fast
        /medium
        /slow
    /probability
    /value

**Description**





**Output**

dict. value (string), probability (real, 0 to 1), all (dict of classes and their probabilities)


**Application**


Rough estimation of rhythmic speed


**Quality Rating**


Experimental


**References**





highlevel.timbre
----------------

::

    curl http://tabasco.upf.edu/api/sounds/<sound_id>/analysis/highlevel/timbre


**Stats**::

    /all
        /bright
        /dark
    /probability
    /value

**Description**





**Output**

dict. value (string), probability (real, 0 to 1), all (dict of classes and their probabilities)


**Application**


Detect if a sound is bright or dark.


**Quality Rating**


Experimental


**References**





highlevel.voice_instrumental
----------------------------

::

    curl http://tabasco.upf.edu/api/sounds/<sound_id>/analysis/highlevel/voice_instrumental


**Stats**::

    /all
        /instrumental
        /voice
    /probability
    /value

**Description**





**Output**

dict. value (string), probability (real, 0 to 1), all (dict of classes and their probabilities)


**Application**


Detect presence of voice/vocals/singing in a song


**Quality Rating**


Experimental


**References**





Lowlevel Descriptors
>>>>>>>>>>>>>>>>>>>>


lowlevel.average_loudness
-------------------------

::

    curl http://tabasco.upf.edu/api/sounds/<sound_id>/analysis/lowlevel/average_loudness


**Description**


Computes the average loudness of a signal, defined as its energy raised to the power of 0.67


**Output**

real, from 0 to 1


**Application**


segmentation


**Quality Rating**


Stable


**References**


[1] Vickers, E., Automatic Long-Term Loudness and Dynamics Matching, Proceedings of the AES 111th Convention, New York, NY, USA, 2001.



**Distribution Plot**

    .. image:: _static/descriptors/lowlevel.average_loudness.none.png
        :height: 300px


lowlevel.barkbands
------------------

::

    curl http://tabasco.upf.edu/api/sounds/<sound_id>/analysis/lowlevel/barkbands


**Stats**::

    /dmean
    /dmean2
    /dvar
    /dvar2
    /max
    /mean
    /min
    /var

**Description**


This algorithm extracts the 28 Bark band values of a Spectrum. For each bark band the power-spectrum (mag-squared) is summed. The first two bands [0..100] and [100..200] are divided in two for better resolution.


**Output**

real, non-negative. 28 values (or less depending on the sampleRate)


**Application**


Perceptual description of sounds, since the scale ranges from 1 to 24 and corresponds to the first 24 critical bands of hearing.


**Quality Rating**


Stable


**References**


[1] The Bark Frequency Scale, http://ccrma.stanford.edu/~jos/bbt/Bark_Frequency_Scale.html


lowlevel.barkbands_kurtosis
---------------------------

::

    curl http://tabasco.upf.edu/api/sounds/<sound_id>/analysis/lowlevel/barkbands_kurtosis


**Stats**::

    /dmean
    /dmean2
    /dvar
    /dvar2
    /max
    /mean
    /min
    /var

**Description**


The kurtosis gives a measure of the flatness of a distribution around its mean value. A negative kurtosis indicates flatter bark bands. A positive kurtosis indicates peakier bark bands. A kurtosis = 0 indicates bark bands with normal distribution.


**Output**

real


**Application**


Timbral characterization.


**Quality Rating**


Stable


**References**


[1] G. Peeters, A large set of audio features for sound description (similarity and classification) in the CUIDADO project, CUIDADO I.S.T. Project Report, 2004

[2] Variance - Wikipedia, the free encyclopedia, http://en.wikipedia.org/wiki/Variance

[3] Skewness - Wikipedia, the free encyclopedia, http://en.wikipedia.org/wiki/Skewness

[4] Kurtosis - Wikipedia, the free encyclopedia, http://en.wikipedia.org/wiki/Kurtosis




**Distribution Plot**

    .. image:: _static/descriptors/lowlevel.barkbands_kurtosis.mean.png
        :height: 300px


lowlevel.barkbands_skewness
---------------------------

::

    curl http://tabasco.upf.edu/api/sounds/<sound_id>/analysis/lowlevel/barkbands_skewness


**Stats**::

    /dmean
    /dmean2
    /dvar
    /dvar2
    /max
    /mean
    /min
    /var

**Description**


The skewness is a measure of the asymmetry of a distribution around its mean value. A negative skewness indicates bark bands with more energy in the high frequencies. A positive skewness indicates bark bands with more energy in the low frequencies. A skewness = 0 indicates symmetric bark bands. For silence or constants signal, skewness is 0.


**Output**

real


**Application**


Timbral characterization.


**Quality Rating**


Stable


**References**


[1] G. Peeters, A large set of audio features for sound description (similarity and classification) in the CUIDADO project, CUIDADO I.S.T. Project Report, 2004

[2] Variance - Wikipedia, the free encyclopedia, http://en.wikipedia.org/wiki/Variance

[3] Skewness - Wikipedia, the free encyclopedia, http://en.wikipedia.org/wiki/Skewness

[4] Kurtosis - Wikipedia, the free encyclopedia, http://en.wikipedia.org/wiki/Kurtosis




**Distribution Plot**

    .. image:: _static/descriptors/lowlevel.barkbands_skewness.mean.png
        :height: 300px


lowlevel.barkbands_spread
-------------------------

::

    curl http://tabasco.upf.edu/api/sounds/<sound_id>/analysis/lowlevel/barkbands_spread


**Stats**::

    /dmean
    /dmean2
    /dvar
    /dvar2
    /max
    /mean
    /min
    /var

**Description**


The spread is defined as the variance of a distribution around its mean value. It is equal to the 2nd order central moment.


**Output**

real


**Application**


Timbral characterization.


**Quality Rating**


Stable


**References**


[1] G. Peeters, A large set of audio features for sound description (similarity and classification) in the CUIDADO project, CUIDADO I.S.T. Project Report, 2004

[2] Variance - Wikipedia, the free encyclopedia, http://en.wikipedia.org/wiki/Variance

[3] Skewness - Wikipedia, the free encyclopedia, http://en.wikipedia.org/wiki/Skewness

[4] Kurtosis - Wikipedia, the free encyclopedia, http://en.wikipedia.org/wiki/Kurtosis




**Distribution Plot**

    .. image:: _static/descriptors/lowlevel.barkbands_spread.mean.png
        :height: 300px


lowlevel.dissonance
-------------------

::

    curl http://tabasco.upf.edu/api/sounds/<sound_id>/analysis/lowlevel/dissonance


**Stats**::

    /dmean
    /dmean2
    /dvar
    /dvar2
    /max
    /mean
    /min
    /var

**Description**


A perceptual descriptor used to measure the roughness of the sound. based on the fact that two sinusoidal spectral components share a dissonance curve, which values are dependent on their frequency and amplitude relations. the total dissonance is derived by summing up the values for all the components (i.e. the spectral peaks) of a given frame. the dissonance curves are obtained from perceptual experiments conducted in the paper listed below.


**Output**

real, from 0 to 1


**Application**


segmentation


**Quality Rating**


Stable


**References**


[1] R. Plomp, W. J. M. Levelt, Tonal Consonance and Critical Bandwidth, J. Acoust. Soc. Am. 38, 548-560, 1965

[2] Critical Band - Handbook for Acoustic Ecology, http://www.sfu.ca/sonic-studio/handbook/Critical_Band.html

[3] Bark Scale - Wikipedia, the free encyclopedia, http://en.wikipedia.org/wiki/Bark_scale




**Distribution Plot**

    .. image:: _static/descriptors/lowlevel.dissonance.mean.png
        :height: 300px


lowlevel.hfc
------------

::

    curl http://tabasco.upf.edu/api/sounds/<sound_id>/analysis/lowlevel/hfc


**Stats**::

    /dmean
    /dmean2
    /dvar
    /dvar2
    /max
    /mean
    /min
    /var

**Description**


The High Frequency Content measure is a simple measure, taken across a signal spectrum (usually a STFT spectrum), which can be used to characterize the amount of high-frequency content in the signal. In contrast to perceptual measures, this is not based on any evidence about its relevance to human hearing. Despite that, it can be useful for some applications, such as onset detection.


**Output**

real, non-negative


**Application**


Onset detection


**Quality Rating**


Stable


**References**


[1] P. Masri, A. Bateman, Improved Modelling of Attack Transients in Music Analysis-Resynthesis, Digital Music Research Group, University of Bristol, 1996

[2] K. Jensen, T. H. Anderson, Beat Estimation On The Beat, Department of Computer Science, University of Copenhagen, 2003




**Distribution Plot**

    .. image:: _static/descriptors/lowlevel.hfc.mean.png
        :height: 300px


lowlevel.mfcc
-------------

::

    curl http://tabasco.upf.edu/api/sounds/<sound_id>/analysis/lowlevel/mfcc


**Stats**::

    /cov
    /icov
    /mean

**Description**


Computes the mel-frequency cepstrum coefficients. As there is no standard implementation, the MFCC-FB40 is used by default:

 - filterbank of 40 bands from 0 to 11000Hz

 - take the dB value of the spectrum

 - DCT of the 40 bands down to 13 mel coefficients



**Output**

real, matrix of dimensions: number mfcc coefficients per number of frames


**Application**


They have been widely used in speech recognition and also to model music since they provide a compact representation of the spectral envelope.


**Quality Rating**


Stable


**References**


[1] T. Ganchev, N. Fakotakis, G. Kokkinakisi, Comparative Evaluation of Various MFCC Implementations on the Speaker Verification Task, Proceedings of the 10th International Conference on Speech and Computer, Patras, Greece, 2005

[2] Mel-frequency cepstrum - Wikipedia, the free encyclopedia, http://en.wikipedia.org/wiki/Mel_frequency_cepstral_coefficient



lowlevel.pitch
--------------

::

    curl http://tabasco.upf.edu/api/sounds/<sound_id>/analysis/lowlevel/pitch


**Stats**::

    /dmean
    /dmean2
    /dvar
    /dvar2
    /max
    /mean
    /min
    /var

**Description**


Pitch detection for monophonic sounds. Pitch is represented as the fundamental frequency of the analysed sound. The algorithm uses the YinFFT method developed by Paul Brossier, based on the time-domain YIN algorithm with an efficient implementation making use of the spectral domain.


**Output**

real, non-negative. Represents the frequency in Hertz.


**Application**


Monophonic voice and instrument transcription


**Quality Rating**


Stable


**References**


[1] P. Brossier, Automatic Annotation of Musical Audio for Interactive Applications, Centre for Digital Music, Queen Mary University of London, 2007

[2] Pitch detection algorithm - Wikipedia, the free encyclopedia, http://en.wikipedia.org/wiki/Pitch_detection_algorithm




**Distribution Plot**

    .. image:: _static/descriptors/lowlevel.pitch.mean.png
        :height: 300px


lowlevel.pitch_instantaneous_confidence
---------------------------------------

::

    curl http://tabasco.upf.edu/api/sounds/<sound_id>/analysis/lowlevel/pitch_instantaneous_confidence


**Stats**::

    /dmean
    /dmean2
    /dvar
    /dvar2
    /max
    /mean
    /min
    /var

**Description**


A measure of pitch confidence derived from the yinFFT algorithm, which is a monophonic pitch detector. gives evidence about how much a certain pitch, detected in a frame, is affecting the total spectrum. If the output is near 1, there exist just one pitch in the mixture, an output near 0 indicates multiple, not distinguishable pitches.


**Output**

real, from 0 to 1.


**Application**


segmentation


**Quality Rating**


Stable


**References**


[1] P. Brossier, Automatic Annotation of Musical Audio for Interactive Applications, Centre for Digital Music, Queen Mary University of London, 2007

[2] Pitch detection algorithm - Wikipedia, the free encyclopedia, http://en.wikipedia.org/wiki/Pitch_detection_algorithm




**Distribution Plot**

    .. image:: _static/descriptors/lowlevel.pitch_instantaneous_confidence.mean.png
        :height: 300px


lowlevel.pitch_salience
-----------------------

::

    curl http://tabasco.upf.edu/api/sounds/<sound_id>/analysis/lowlevel/pitch_salience


**Stats**::

    /dmean
    /dmean2
    /dvar
    /dvar2
    /max
    /mean
    /min
    /var

**Description**


The pitch salience is given by the ratio of the highest peak to the 0-lag peak in the autocorrelation function. Non-pitched sounds have a mean pitch salience value close to 0 while harmonic sounds have a value close to 1. Sounds having Unvarying pitch have a small pitch salience variance while sounds having Varying pitch have a high pitch salience variance.


**Output**

real, from 0 to 1


**Application**


Characterizing percussive sounds for example. We can expect low values for percussive sounds and high values for white noises.


**Quality Rating**


Stable


**References**






**Distribution Plot**

    .. image:: _static/descriptors/lowlevel.pitch_salience.mean.png
        :height: 300px


lowlevel.silence_rate_60dB
--------------------------

::

    curl http://tabasco.upf.edu/api/sounds/<sound_id>/analysis/lowlevel/silence_rate_60dB


**Stats**::

    /dmean
    /dmean2
    /dvar
    /dvar2
    /max
    /mean
    /min
    /var

**Description**


This is the rate of frames where the level is above a given threshold, here -60dB. Returns 1 whenever the instant power of the input frame is below the given threshold, 0 otherwise


**Output**

binary, 0 or 1


**Application**


Measure the level of compression of a signal.


**Quality Rating**


Stable


**References**






**Distribution Plot**

    .. image:: _static/descriptors/lowlevel.silence_rate_60dB.mean.png
        :height: 300px


lowlevel.spectral_centroid
--------------------------

::

    curl http://tabasco.upf.edu/api/sounds/<sound_id>/analysis/lowlevel/spectral_centroid


**Stats**::

    /dmean
    /dmean2
    /dvar
    /dvar2
    /max
    /mean
    /min
    /var

**Description**


The spectral centroid is a measure used in digital signal processing to characterize an audio spectrum. It indicates where the "center of mass" of the spectrum is.


**Output**

real, non-negative


**Application**


Perceptually, it has a robust connection with the impression of "brightness" of a sound. High values of it correspond to brighter textures.


**Quality Rating**


Stable


**References**


Function Centroid -- from Wolfram MathWorld, http://mathworld.wolfram.com/FunctionCentroid.html



**Distribution Plot**

    .. image:: _static/descriptors/lowlevel.spectral_centroid.mean.png
        :height: 300px


lowlevel.spectral_complexity
----------------------------

::

    curl http://tabasco.upf.edu/api/sounds/<sound_id>/analysis/lowlevel/spectral_complexity


**Stats**::

    /dmean
    /dmean2
    /dvar
    /dvar2
    /max
    /mean
    /min
    /var

**Description**


Timbral Complexity is a measure of the complexity of the instrumentation of the audio piece. Typically, in a piece of audio several instruments are present. This increases the complexity of the spectrum of the audio and therefore, it represents a useful audio feature for characterizing a piece of audio.


**Output**

integer, non-negative


**Application**


segmentation


**Quality Rating**


Stable


**References**






**Distribution Plot**

    .. image:: _static/descriptors/lowlevel.spectral_complexity.mean.png
        :height: 300px


lowlevel.spectral_contrast
--------------------------

::

    curl http://tabasco.upf.edu/api/sounds/<sound_id>/analysis/lowlevel/spectral_contrast


**Stats**::

    /mean
    /var

**Description**


The Spectral Contrast feature is based on the Octave Based Spectral Contrast feature as described in [1]. The version implemented here is a modified version to improve discriminative power and robustness. The modifications are described in [2].


**Output**

vector of real values


**Application**





**Quality Rating**


Stable


**References**


[1] Dan-Ning Jiang, Lie Lu, Hong-Jiang Zhang, Jian-Hua Tao, Lian-Hong Cai, Music Type Classification by Spectral Contrast Feature, 2002.

[2] Vincent Akkermans, Joan Serra, Perfecto Herrera, Shape Based Spectral Contrast feature, 2009.



lowlevel.spectral_crest
-----------------------

::

    curl http://tabasco.upf.edu/api/sounds/<sound_id>/analysis/lowlevel/spectral_crest


**Stats**::

    /dmean
    /dmean2
    /dvar
    /dvar2
    /max
    /mean
    /min
    /var

**Description**


The crest is the ratio between the max value and the arithmetic mean of the spectrum. It is a measure of the noisiness of the spectrum.


**Output**

real, greater than 1.


**Application**


Discrimination of noisy signals


**Quality Rating**


Stable


**References**


[1] G. Peeters, A large set of audio features for sound description (similarity and classification) in the CUIDADO project, CUIDADO I.S.T. Project Report, 2004



**Distribution Plot**

    .. image:: _static/descriptors/lowlevel.spectral_crest.mean.png
        :height: 300px


lowlevel.spectral_decrease
--------------------------

::

    curl http://tabasco.upf.edu/api/sounds/<sound_id>/analysis/lowlevel/spectral_decrease


**Stats**::

    /dmean
    /dmean2
    /dvar
    /dvar2
    /max
    /mean
    /min
    /var

**Description**


This algorithm extracts the decrease of an array of Reals (which is defined as the linear regression coefficient). The range parameter is used to normalize the result. For a spectral centroid, the range should be equal to Nyquist and for an audio centroid the range should be equal to (audiosize - 1) / samplerate.


**Output**

a real number normalized by the range parameter


**Application**


Classification of musical instruments, pitch detection for some specific instruments like the piano


**Quality Rating**


Stable


**References**


[1] Least Squares Fitting -- from Wolfram MathWorld, http://mathworld.wolfram.com/LeastSquaresFitting.html



**Distribution Plot**

    .. image:: _static/descriptors/lowlevel.spectral_decrease.mean.png
        :height: 300px


lowlevel.spectral_energy
------------------------

::

    curl http://tabasco.upf.edu/api/sounds/<sound_id>/analysis/lowlevel/spectral_energy


**Stats**::

    /dmean
    /dmean2
    /dvar
    /dvar2
    /max
    /mean
    /min
    /var

**Description**


The spectrum energy at a given frame.


**Output**

real, non-negative


**Application**





**Quality Rating**


Stable


**References**


1] Energy (signal processing) - Wikipedia, the free encyclopedia, http://en.wikipedia.org/wiki/Energy_(signal_processing)



**Distribution Plot**

    .. image:: _static/descriptors/lowlevel.spectral_energy.mean.png
        :height: 300px


lowlevel.spectral_energyband_high
---------------------------------

::

    curl http://tabasco.upf.edu/api/sounds/<sound_id>/analysis/lowlevel/spectral_energyband_high


**Stats**::

    /dmean
    /dmean2
    /dvar
    /dvar2
    /max
    /mean
    /min
    /var

**Description**


The Energy Band Ratio of a spectrum is the ratio of the spectrum energy from startCutoffFrequency to stopCutoffFrequency to the total spectrum energy. For the Energy Band Ration High, startCutoffFrequency = 4000Hz and stopCutoffFrequency = 20000Hz


**Output**

real, from 0 to 1


**Application**





**Quality Rating**


Stable


**References**


[1] Energy (signal processing) - Wikipedia, the free encyclopedia, http://en.wikipedia.org/wiki/Energy_(signal_processing)



**Distribution Plot**

    .. image:: _static/descriptors/lowlevel.spectral_energyband_high.mean.png
        :height: 300px


lowlevel.spectral_energyband_low
--------------------------------

::

    curl http://tabasco.upf.edu/api/sounds/<sound_id>/analysis/lowlevel/spectral_energyband_low


**Stats**::

    /dmean
    /dmean2
    /dvar
    /dvar2
    /max
    /mean
    /min
    /var

**Description**


The Energy Band Ratio of a spectrum is the ratio of the spectrum energy from startCutoffFrequency to stopCutoffFrequency to the total spectrum energy. For the Energy Band Ration Low, startCutoffFrequency = 20Hz and stopCutoffFrequency = 150Hz


**Output**

real, from 0 to 1


**Application**





**Quality Rating**


Stable


**References**


[1] Energy (signal processing) - Wikipedia, the free encyclopedia, http://en.wikipedia.org/wiki/Energy_(signal_processing)



**Distribution Plot**

    .. image:: _static/descriptors/lowlevel.spectral_energyband_low.mean.png
        :height: 300px


lowlevel.spectral_energyband_middle_high
----------------------------------------

::

    curl http://tabasco.upf.edu/api/sounds/<sound_id>/analysis/lowlevel/spectral_energyband_middle_high


**Stats**::

    /dmean
    /dmean2
    /dvar
    /dvar2
    /max
    /mean
    /min
    /var

**Description**


The Energy Band Ratio of a spectrum is the ratio of the spectrum energy from startCutoffFrequency to stopCutoffFrequency to the total spectrum energy. For the Energy Band Ration Middle High, startCutoffFrequency = 800Hz and stopCutoffFrequency = 4000Hz


**Output**

real, from 0 to 1


**Application**





**Quality Rating**


Stable


**References**


[1] Energy (signal processing) - Wikipedia, the free encyclopedia, http://en.wikipedia.org/wiki/Energy_(signal_processing)



**Distribution Plot**

    .. image:: _static/descriptors/lowlevel.spectral_energyband_middle_high.mean.png
        :height: 300px


lowlevel.spectral_energyband_middle_low
---------------------------------------

::

    curl http://tabasco.upf.edu/api/sounds/<sound_id>/analysis/lowlevel/spectral_energyband_middle_low


**Stats**::

    /dmean
    /dmean2
    /dvar
    /dvar2
    /max
    /mean
    /min
    /var

**Description**


The Energy Band Ratio of a spectrum is the ratio of the spectrum energy from startCutoffFrequency to stopCutoffFrequency to the total spectrum energy. For the Energy Band Ration Middle Low, startCutoffFrequency = 150Hz and stopCutoffFrequency = 800Hz


**Output**

real, from 0 to 1


**Application**





**Quality Rating**


Stable


**References**


[1] Energy (signal processing) - Wikipedia, the free encyclopedia, http://en.wikipedia.org/wiki/Energy_(signal_processing)



**Distribution Plot**

    .. image:: _static/descriptors/lowlevel.spectral_energyband_middle_low.mean.png
        :height: 300px


lowlevel.spectral_flatness_db
-----------------------------

::

    curl http://tabasco.upf.edu/api/sounds/<sound_id>/analysis/lowlevel/spectral_flatness_db


**Stats**::

    /dmean
    /dmean2
    /dvar
    /dvar2
    /max
    /mean
    /min
    /var

**Description**


This is a kind of dB value of the Bark bands. It characterizes the shape of the spectral envelope. For tonal signals, flatness dB is close to 1, for noisy signals it is close to 0.


**Output**

real, from 0 to 1.


**Application**


segmentation


**Quality Rating**


Stable


**References**






**Distribution Plot**

    .. image:: _static/descriptors/lowlevel.spectral_flatness_db.mean.png
        :height: 300px


lowlevel.spectral_flux
----------------------

::

    curl http://tabasco.upf.edu/api/sounds/<sound_id>/analysis/lowlevel/spectral_flux


**Stats**::

    /dmean
    /dmean2
    /dvar
    /dvar2
    /max
    /mean
    /min
    /var

**Description**


Spectral Flux is a measure of how quickly the power spectrum of a signal is changing, calculated by comparing the power spectrum for one frame against the power spectrum from the previous frame. The spectral flux can be used to determine the timbre of an audio signal, or in onset detection, among other things.


**Output**

a positive real number


**Application**


segmentation


**Quality Rating**


Stable


**References**


[1] Tzanetakis, G., Cook, P., "Multifeature Audio Segmentation for Browsing and Annotation", Proceedings of the 1999 IEEE Workshop on Applications of Signal Processing to Audio and Acoustics, New Paltz, NY, USA, 1999, W99 1-4.



**Distribution Plot**

    .. image:: _static/descriptors/lowlevel.spectral_flux.mean.png
        :height: 300px


lowlevel.spectral_kurtosis
--------------------------

::

    curl http://tabasco.upf.edu/api/sounds/<sound_id>/analysis/lowlevel/spectral_kurtosis


**Stats**::

    /dmean
    /dmean2
    /dvar
    /dvar2
    /max
    /mean
    /min
    /var

**Description**


The kurtosis gives a measure of the flatness of a distribution around its mean value. A negative kurtosis indicates a flatter signal spectrum. A positive kurtosis indicates a peakier signal spectrum. A kurtosis = 0 indicates a spectrum with normal distribution.


**Output**

real


**Application**


Timbral characterization.


**Quality Rating**


Stable


**References**


[1] G. Peeters, A large set of audio features for sound description (similarity and classification) in the CUIDADO project, CUIDADO I.S.T. Project Report, 2004

[2] Variance - Wikipedia, the free encyclopedia, http://en.wikipedia.org/wiki/Variance

[3] Skewness - Wikipedia, the free encyclopedia, http://en.wikipedia.org/wiki/Skewness

[4] Kurtosis - Wikipedia, the free encyclopedia, http://en.wikipedia.org/wiki/Kurtosis




**Distribution Plot**

    .. image:: _static/descriptors/lowlevel.spectral_kurtosis.mean.png
        :height: 300px


lowlevel.spectral_rms
---------------------

::

    curl http://tabasco.upf.edu/api/sounds/<sound_id>/analysis/lowlevel/spectral_rms


**Stats**::

    /dmean
    /dmean2
    /dvar
    /dvar2
    /max
    /mean
    /min
    /var

**Description**


The root mean square spectrum energy.


**Output**

real, non-negative


**Application**


a measure of loudness of the sound frame


**Quality Rating**


Stable


**References**


[1] Root mean square - Wikipedia, the free encyclopedia, http://en.wikipedia.org/wiki/Root_mean_square



**Distribution Plot**

    .. image:: _static/descriptors/lowlevel.spectral_rms.mean.png
        :height: 300px


lowlevel.spectral_rolloff
-------------------------

::

    curl http://tabasco.upf.edu/api/sounds/<sound_id>/analysis/lowlevel/spectral_rolloff


**Stats**::

    /dmean
    /dmean2
    /dvar
    /dvar2
    /max
    /mean
    /min
    /var

**Description**


Computes the roll-off frequency of a spectrum. The roll-off frequency is defined as the frequency under which some percentage (cutoff), of the total energy of the spectrum is contained, 85% in this case. The roll-off frequency can be used to distinguish between harmonic (below roll-off) and noisy sounds (above roll-off).


**Output**

real, from 0 to 22500


**Application**


To distinguish between harmonic and noisy sounds.


**Quality Rating**


Stable


**References**






**Distribution Plot**

    .. image:: _static/descriptors/lowlevel.spectral_rolloff.mean.png
        :height: 300px


lowlevel.spectral_skewness
--------------------------

::

    curl http://tabasco.upf.edu/api/sounds/<sound_id>/analysis/lowlevel/spectral_skewness


**Stats**::

    /dmean
    /dmean2
    /dvar
    /dvar2
    /max
    /mean
    /min
    /var

**Description**


The skewness is a measure of the asymmetry of a distribution around its mean value. A negative skewness indicates a signal spectrum with more energy in the high frequencies. A positive skewness indicates a signal spectrum with more energy in the low frequencies. A skewness = 0 indicates a symmetric spectrum. For silence or constants signal, skewness is 0.


**Output**

real


**Application**


Timbral characterization.


**Quality Rating**


Stable


**References**


[1] G. Peeters, A large set of audio features for sound description (similarity and classification) in the CUIDADO project, CUIDADO I.S.T. Project Report, 2004

[2] Variance - Wikipedia, the free encyclopedia, http://en.wikipedia.org/wiki/Variance

[3] Skewness - Wikipedia, the free encyclopedia, http://en.wikipedia.org/wiki/Skewness

[4] Kurtosis - Wikipedia, the free encyclopedia, http://en.wikipedia.org/wiki/Kurtosis




**Distribution Plot**

    .. image:: _static/descriptors/lowlevel.spectral_skewness.mean.png
        :height: 300px


lowlevel.spectral_spread
------------------------

::

    curl http://tabasco.upf.edu/api/sounds/<sound_id>/analysis/lowlevel/spectral_spread


**Stats**::

    /dmean
    /dmean2
    /dvar
    /dvar2
    /max
    /mean
    /min
    /var

**Description**


The spread is defined as the variance of a distribution around its mean value. It is equal to the 2nd order central moment.


**Output**

real


**Application**


Timbral characterization.


**Quality Rating**


Stable


**References**


[1] G. Peeters, A large set of audio features for sound description (similarity and classification) in the CUIDADO project, CUIDADO I.S.T. Project Report, 2004

[2] Variance - Wikipedia, the free encyclopedia, http://en.wikipedia.org/wiki/Variance

[3] Skewness - Wikipedia, the free encyclopedia, http://en.wikipedia.org/wiki/Skewness

[4] Kurtosis - Wikipedia, the free encyclopedia, http://en.wikipedia.org/wiki/Kurtosis




**Distribution Plot**

    .. image:: _static/descriptors/lowlevel.spectral_spread.mean.png
        :height: 300px


lowlevel.spectral_strongpeak
----------------------------

::

    curl http://tabasco.upf.edu/api/sounds/<sound_id>/analysis/lowlevel/spectral_strongpeak


**Stats**::

    /dmean
    /dmean2
    /dvar
    /dvar2
    /max
    /mean
    /min
    /var

**Description**


The Strong Peak is defined as the ratio between the spectrum maximum magnitude and the bandwidth of the maximum peak in the spectrum above a threshold (half its amplitude). It reveals whether the spectrum presents a very pronounced maximum peak. The thinner and the higher the maximum of the spectrum is, the higher the value this parameter takes.


**Output**

a positive real number


**Application**


Recognition of percussive instruments


**Quality Rating**


Stable


**References**


[1] Gouyon, F. and Herrera, P., Exploration of techniques for automatic labelling of audio drum tracks instruments, Music Technology Group, Pompeu Fabra University, 2001



**Distribution Plot**

    .. image:: _static/descriptors/lowlevel.spectral_strongpeak.mean.png
        :height: 300px


lowlevel.zerocrossingrate
-------------------------

::

    curl http://tabasco.upf.edu/api/sounds/<sound_id>/analysis/lowlevel/zerocrossingrate


**Stats**::

    /dmean
    /dmean2
    /dvar
    /dvar2
    /max
    /mean
    /min
    /var

**Description**


The Zero Crossing Rate is the number of sign changes between consecutive signal values divided by the total number of values.


**Output**

real, from 0 to 1


**Application**


A measure of the noisiness of the signal: noisy signals tend to have a high value.


**Quality Rating**


Stable


**References**


[1] Zero Crossing - Wikipedia, the free encyclopedia, http://en.wikipedia.org/wiki/Zero_crossing



**Distribution Plot**

    .. image:: _static/descriptors/lowlevel.zerocrossingrate.mean.png
        :height: 300px


Rhythm Descriptors
>>>>>>>>>>>>>>>>>>


rhythm.beats_loudness
---------------------

::

    curl http://tabasco.upf.edu/api/sounds/<sound_id>/analysis/rhythm/beats_loudness


**Stats**::

    /dmean
    /dmean2
    /dvar
    /dvar2
    /max
    /mean
    /min
    /var

**Description**


Beats loudness is a measure of the strength of the rhythmic beats of the audio piece. It turns to be very useful for characterizing audio piece.


**Output**

real, from 0 to 1


**Application**


Genre classification. For example, a folk song may have a low beats loudness while a punk-rock song or a hip-hop song may have a high beats loudness.


**Quality Rating**


Stable


**References**






**Distribution Plot**

    .. image:: _static/descriptors/rhythm.beats_loudness.mean.png
        :height: 300px


rhythm.beats_loudness_bass
--------------------------

::

    curl http://tabasco.upf.edu/api/sounds/<sound_id>/analysis/rhythm/beats_loudness_bass


**Stats**::

    /dmean
    /dmean2
    /dvar
    /dvar2
    /max
    /mean
    /min
    /var

**Description**


Beats loudness bass is a measure of the strength of the low frequency part of rhythmic beats of an audio piece. It turns to be very useful for characterizing an audio piece.


**Output**

real, from 0 to 1


**Application**


Genre Classification. For example, a folk song or a punk-rock may have a low beats loudness bass, while a hip-hop song may have a high bass beats loudness bass.


**Quality Rating**


Stable


**References**






**Distribution Plot**

    .. image:: _static/descriptors/rhythm.beats_loudness_bass.mean.png
        :height: 300px


rhythm.beats_position
---------------------

::

    curl http://tabasco.upf.edu/api/sounds/<sound_id>/analysis/rhythm/beats_position


**Description**


This descriptor gives the position of the beats in a track, where a beat is one quarter note according to the determined tempo of the track. It is given in the "ticks" output of the StreamingTempoTap algorithm.


**Output**

The location of the beats, in seconds (i.e. Real non-negative)


**Application**


Score alignment


**Quality Rating**


Stable


**References**


[1] F. Gouyon, A computational approach to rhythm description -- Audio features for the computation of rhythm periodicity functions and their use in tempo induction and music content processing. Music Technology Group, Pompeu Fabra University, 2005

[2] M. Davies and M. Plumbley, Causal tempo tracking of audio, 5th International Symposium on Music Information Retrieval, 2004



rhythm.bpm
----------

::

    curl http://tabasco.upf.edu/api/sounds/<sound_id>/analysis/rhythm/bpm


**Description**


BPM (Beat Per Minute) is a measure of tempo. The higher the BPM is the faster is the tempo. A BPM value of 120 means that there are 120 beats per minute, typically 120 quarter notes per minute.


**Output**

real value from 40 to 208


**Application**


Segmentation, Genre classification, Mood classification.


**Quality Rating**


Stable


**References**


[1] F. Gouyon, A computational approach to rhythm description -- Audio features for the computation of rhythm periodicity functions and their use in tempo induction and music content processing. Music Technology Group, Pompeu Fabra University, 2005

[2] M. Davies and M. Plumbley, Causal tempo tracking of audio, 5th International Symposium on Music Information Retrieval, 2004




**Distribution Plot**

    .. image:: _static/descriptors/rhythm.bpm.none.png
        :height: 300px


rhythm.bpm_estimates
--------------------

::

    curl http://tabasco.upf.edu/api/sounds/<sound_id>/analysis/rhythm/bpm_estimates


**Description**


List of estimated BPM values.


**Output**

a vector of real (bpm)


**Application**


Tempo tracking


**Quality Rating**


Stable


**References**


[1] F. Gouyon, A computational approach to rhythm description -- Audio features for the computation of rhythm periodicity functions and their use in tempo induction and music content processing. Music Technology Group, Pompeu Fabra University, 2005

[2] M. Davies and M. Plumbley, Causal tempo tracking of audio, 5th International Symposium on Music Information Retrieval, 2004



rhythm.bpm_intervals
--------------------

::

    curl http://tabasco.upf.edu/api/sounds/<sound_id>/analysis/rhythm/bpm_intervals


**Description**


List of beats interval in seconds. It estimates the time in seconds between two beats. At each frame, an estimation is added to the list.


**Output**

a real vector of real (interval between beats in seconds)


**Application**


Tempo tracking


**Quality Rating**


Stable


**References**


[1] F. Gouyon, A computational approach to rhythm description -- Audio features for the computation of rhythm periodicity functions and their use in tempo induction and music content processing. Music Technology Group, Pompeu Fabra University, 2005

[2] M. Davies and M. Plumbley, Causal tempo tracking of audio, 5th International Symposium on Music Information Retrieval, 2004



rhythm.first_peak_bpm
---------------------

::

    curl http://tabasco.upf.edu/api/sounds/<sound_id>/analysis/rhythm/first_peak_bpm


**Description**


This algorithm computes the value of the highest peak of the bpm probability histogram.


**Output**

real, non-negative


**Application**


Genre classification; beat estimation.


**Quality Rating**


Stable


**References**






**Distribution Plot**

    .. image:: _static/descriptors/rhythm.first_peak_bpm.none.png
        :height: 300px


rhythm.first_peak_spread
------------------------

::

    curl http://tabasco.upf.edu/api/sounds/<sound_id>/analysis/rhythm/first_peak_spread


**Description**


This algorithm computes the spread of the highest peak of the bpm probability histogram. The spread is defined as the variance of a distribution around its mean value. It is equal to the 2nd order central moment.


**Output**

real, non-negative


**Application**


Genre classification; beat estimation.


**Quality Rating**


Stable


**References**






**Distribution Plot**

    .. image:: _static/descriptors/rhythm.first_peak_spread.none.png
        :height: 300px


rhythm.first_peak_weight
------------------------

::

    curl http://tabasco.upf.edu/api/sounds/<sound_id>/analysis/rhythm/first_peak_weight


**Description**


This algorithm computes the weight of the highest peak of the bpm probability histogram.


**Output**

real, non-negative


**Application**


Genre classification; beat estimation.


**Quality Rating**


Stable


**References**






**Distribution Plot**

    .. image:: _static/descriptors/rhythm.first_peak_weight.none.png
        :height: 300px


rhythm.onset_rate
-----------------

::

    curl http://tabasco.upf.edu/api/sounds/<sound_id>/analysis/rhythm/onset_rate


**Description**


The onset is the beginning of a note or a sound, in which the amplitude of the sounds rises from zero to an initial peak. The onset rate is a real number representing the number of onsets per second. It may also be considered as a measure of the number of sonic events per second, and thus a rhythmic indicator of the audio piece. A higher onset rate means that the audio piece has a higher rhythmic density.


**Output**

real, non-negative


**Application**


Rhythm detection


**Quality Rating**


Stable


**References**






**Distribution Plot**

    .. image:: _static/descriptors/rhythm.onset_rate.none.png
        :height: 300px


rhythm.onset_times
------------------

::

    curl http://tabasco.upf.edu/api/sounds/<sound_id>/analysis/rhythm/onset_times


**Description**


The onset is the beginning of a note or a sound, in which the amplitude of the sound rises from zero to an initial peak. The onsets are the time stamps in seconds corresponding to the onsets of the audio piece.


**Output**

real, positive. Array of real values.


**Application**


Rhythm detection


**Quality Rating**


Stable


**References**


[1] P. Brossier, J. P. Bello, M. D. Plumbley, Fast labelling of notes in music signals, Proceedings of the 5th International Conference on Music Information Retrieval, Barcelona, Spain, 2004


rhythm.rubato_start
-------------------

::

    curl http://tabasco.upf.edu/api/sounds/<sound_id>/analysis/rhythm/rubato_start


**Description**


This descriptor provides a list of values indicating the start times, in seconds, of large tempo changes in the signal.


**Output**

real, positive. Array of real values.


**Application**


Measure fluctuation in tempo or rhythm


**Quality Rating**


Stable


**References**


[1] Tempo Rubato - Wikipedia, the free encyclopedia, http://en.wikipedia.org/wiki/Rubato


rhythm.rubato_stop
------------------

::

    curl http://tabasco.upf.edu/api/sounds/<sound_id>/analysis/rhythm/rubato_stop


**Description**


This descriptor provides a list of values indicating the stop times, in seconds, of large tempo changes in the signal.


**Output**

real, positive. Array of real values.


**Application**


Measure fluctuation in tempo or rhythm


**Quality Rating**


Stable


**References**


[1] Tempo Rubato - Wikipedia, the free encyclopedia, http://en.wikipedia.org/wiki/Rubato


rhythm.second_peak_bpm
----------------------

::

    curl http://tabasco.upf.edu/api/sounds/<sound_id>/analysis/rhythm/second_peak_bpm


**Description**


This algorithm computes the value of the second highest peak of the bpm probability histogram.


**Output**

real, non-negative


**Application**


Genre classification; beat estimation.


**Quality Rating**


Stable


**References**






**Distribution Plot**

    .. image:: _static/descriptors/rhythm.second_peak_bpm.none.png
        :height: 300px


rhythm.second_peak_spread
-------------------------

::

    curl http://tabasco.upf.edu/api/sounds/<sound_id>/analysis/rhythm/second_peak_spread


**Description**


This algorithm computes the spread of the second highest peak of the bpm probability histogram. The spread is defined as the variance of a distribution around its mean value. It is equal to the 2nd order central moment.


**Output**

real, non-negative


**Application**


Genre classification; beat estimation.


**Quality Rating**


Stable


**References**






**Distribution Plot**

    .. image:: _static/descriptors/rhythm.second_peak_spread.none.png
        :height: 300px


rhythm.second_peak_weight
-------------------------

::

    curl http://tabasco.upf.edu/api/sounds/<sound_id>/analysis/rhythm/second_peak_weight


**Description**


This algorithm computes the weight of the second highest peak of the bpm probability histogram.


**Output**

real, non-negative


**Application**


Genre classification; beat estimation.


**Quality Rating**


Stable


**References**






**Distribution Plot**

    .. image:: _static/descriptors/rhythm.second_peak_weight.none.png
        :height: 300px


Sfx Descriptors
>>>>>>>>>>>>>>>


sfx.inharmonicity
-----------------

::

    curl http://tabasco.upf.edu/api/sounds/<sound_id>/analysis/sfx/inharmonicity


**Stats**::

    /dmean
    /dmean2
    /dvar
    /dvar2
    /max
    /mean
    /min
    /var

**Description**


The divergence of the signal spectral components from a purely harmonic signal. It is computed as the energy weighted divergence of the spectral components from the multiple of the fundamental frequency. The inharmonicity ranges from 0 (purely harmonic signal) to 1 (inharmonic signal).


**Output**

real, from 0 to 1.


**Application**


Characterization of piano sounds


**Quality Rating**


Stable


**References**


[1] Inharmonicity - Wikipedia, the free encyclopedia, http://en.wikipedia.org/wiki/Inharmonicity



**Distribution Plot**

    .. image:: _static/descriptors/sfx.inharmonicity.mean.png
        :height: 300px


sfx.oddtoevenharmonicenergyratio
--------------------------------

::

    curl http://tabasco.upf.edu/api/sounds/<sound_id>/analysis/sfx/oddtoevenharmonicenergyratio


**Stats**::

    /dmean
    /dmean2
    /dvar
    /dvar2
    /max
    /mean
    /min
    /var

**Description**


The Odd to Even Harmonic Energy Ratio of a signal given its harmonic peaks. The Odd to Even Harmonic Energy Ratio is a measure allowing distinguishing odd harmonic energy predominant sounds (such as clarinet sounds) from equally important harmonic energy sounds (such as the trumpet).


**Output**

real, from 0 to 1.


**Application**


Discrimination of sounds with predominance of odd or even harmonics


**Quality Rating**


Stable


**References**


[1] Martin, K. D., Kim, Y. E., Musical Instrument Identification: A Pattern-Recognition Approach, MIT Media Lab Machine Listening Group, Presented at the 136th meeting of the Acoustical Society of America, October 13, 1998, http://sound.media.mit.edu/Papers/kdm-asa98.pdf

[2] Ringgenberg, K., et. al., Musical Instrument Recognition, https://trac.rhaptos.org/~cbearden/Print20080130/col10313.pdf




**Distribution Plot**

    .. image:: _static/descriptors/sfx.oddtoevenharmonicenergyratio.mean.png
        :height: 300px


sfx.pitch_after_max_to_before_max_energy_ratio
----------------------------------------------

::

    curl http://tabasco.upf.edu/api/sounds/<sound_id>/analysis/sfx/pitch_after_max_to_before_max_energy_ratio


**Description**


The ratio of energy after the maximum to energy before the maximum of pitch values. Sounds having an ascending pitch value a small while sounds having a descending pitch have a high value.


**Output**

real, from 0 to 1.


**Application**


Discriminating sounds with different relation between pitch and energy envelope


**Quality Rating**


Stable


**References**






**Distribution Plot**

    .. image:: _static/descriptors/sfx.pitch_after_max_to_before_max_energy_ratio.none.png
        :height: 300px


sfx.pitch_centroid
------------------

::

    curl http://tabasco.upf.edu/api/sounds/<sound_id>/analysis/sfx/pitch_centroid


**Description**


The center of gravity of the array of pitch values per frame. A value close to 0.5 may indicate a stable pitch


**Output**

a real number normalized by the range parameter


**Application**


Classifying sound effects with a potentially varying pitch.


**Quality Rating**


Stable


**References**


[1] Function Centroid -- from Wolfram MathWorld, http://mathworld.wolfram.com/FunctionCentroid.html



**Distribution Plot**

    .. image:: _static/descriptors/sfx.pitch_centroid.none.png
        :height: 300px


sfx.pitch_max_to_total
----------------------

::

    curl http://tabasco.upf.edu/api/sounds/<sound_id>/analysis/sfx/pitch_max_to_total


**Description**


A measure of the relative position in time of the maximum pitch value. A value of zero (maximum at the beginning) indicates descending pitch, while a value of one indicates an ascending pitch.


**Output**

real, from 0 to 1.


**Application**


Discriminating sound effects with different pitch envelopes


**Quality Rating**


Stable


**References**






**Distribution Plot**

    .. image:: _static/descriptors/sfx.pitch_max_to_total.none.png
        :height: 300px


sfx.pitch_min_to_total
----------------------

::

    curl http://tabasco.upf.edu/api/sounds/<sound_id>/analysis/sfx/pitch_min_to_total


**Description**


A measure of the relative position in time of the minimum pitch value. A value of zero (minimum at the beginning) indicates ascending pitch, while a value of one indicates an descending pitch.


**Output**

real, from 0 to 1.


**Application**


Discriminating sound effects with different pitch envelopes


**Quality Rating**


Stable


**References**






**Distribution Plot**

    .. image:: _static/descriptors/sfx.pitch_min_to_total.none.png
        :height: 300px


sfx.tristimulus
---------------

::

    curl http://tabasco.upf.edu/api/sounds/<sound_id>/analysis/sfx/tristimulus


**Stats**::

    /dmean
    /dmean2
    /dvar
    /dvar2
    /max
    /mean
    /min
    /var

**Description**


The concept of tristimulus was introduced as an equivalent for timbre to the three primary colors of vision. The tristimuli are 3 different types of energy ratio: the first value corresponds to the relative weight of the first harmonic, the second to that of the 2nd, 3rd, and 4th harmonics, and the third to the weight of the rest.


**Output**

a list of 3 real values from 0 to 1


**Application**


Characterization of timbre.


**Quality Rating**


Stable


**References**


[1] Tristimulus (audio) - Wikipedia, the free encyclopedia http://en.wikipedia.org/wiki/Tristimulus_(audio)


Tonal Descriptors
>>>>>>>>>>>>>>>>>


tonal.chords_changes_rate
-------------------------

::

    curl http://tabasco.upf.edu/api/sounds/<sound_id>/analysis/tonal/chords_changes_rate


**Description**


The Chord Changes Rate is the ratio from the number of "tonal_chords_changes" to the total number of detected chords in "tonal_chord_progression".


**Output**

real, from 0 to 1.


**Application**


Similarity, classification


**Quality Rating**


Stable


**References**


[1] Chord progression - Wikipedia, the free encyclopedia, http://en.wikipedia.org/wiki/Chord_progression

[2] Circle of fifths - Wikipedia, the free encyclopedia, http://en.wikipedia.org/wiki/Circle_of_fifths




**Distribution Plot**

    .. image:: _static/descriptors/tonal.chords_changes_rate.none.png
        :height: 300px


tonal.chords_histogram
----------------------

::

    curl http://tabasco.upf.edu/api/sounds/<sound_id>/analysis/tonal/chords_histogram


**Description**


The Chords Histogram represents, for each possible chord, the percentage of times this chord is played in the audio piece, following the "tonal_chords_progression". The histogram "normalized" to the "tonal_key_key" following the circle of fifth.

Output domain: real, from 0 to 100. Returns a list of 24 values (from 0 to 100) representing the chords in the following order (circle of fifths): C, Em, G, Bm, D, F::m, A, C::m, E, G::m, B, D::m, F#, A::m, C#, Fm, G#, Cm, D#, Gm, A#, Dm, F, Am



**Output**

real, from 0 to 100. Returns a list of 24 values (from 0 to 100) representing the chords in the following order (circle of fifths): C, Em, G, Bm, D, F::m, A, C::m, E, G::m, B, D::m, F#, A::m, C#, Fm, G#, Cm, D#, Gm, A#, Dm, F, Am


**Application**


Harmonic description and similarity.


**Quality Rating**


Stable


**References**


[1] Chord progression - Wikipedia, the free encyclopedia, http://en.wikipedia.org/wiki/Chord_progression

[2] Circle of fifths - Wikipedia, the free encyclopedia, http://en.wikipedia.org/wiki/Circle_of_fifths



tonal.chords_key
----------------

::

    curl http://tabasco.upf.edu/api/sounds/<sound_id>/analysis/tonal/chords_key


**Description**


A chord is made of three (triad) or more notes that sound simultaneously. Each chord is specified by its root/bass note (what we call "key" A, A#, B, C, C#, D, D#, E, F, F#, G, G#), its type or "mode" (major, minor, major7,...) and its strength (how close the note distribution is from the estimated chord).

A succession of chords is called a chord progression.

The chord is computed using the key estimation algorithm within short segments of 1 or 2 seconds.



**Output**

string. The string represents the chord of the analyzed segment, A, A#, B, C, C#, D, D#, E, F, F#, G, G#


**Application**


Chord estimation, harmonic description.


**Quality Rating**


Stable


**References**


[1] Gomez, E., "Tonal Description of Polyphonic Audio for Music Content Processing", INFORMS Journal On Computing, Vol. 18, No. 3, Summer 2006, pp. 294-304.

[2] Temperley, D. "Whats key for key? The Krumhansl-Schmuckler key-finding algorithm reconsidered", Music Perception 17(1) pp. 65-100, 1999. http://www.links.cs.cmu.edu/music-analysis/key.html




**Distribution Plot**

    .. image:: _static/descriptors/tonal.chords_key.none.png
        :height: 300px


tonal.chords_number_rate
------------------------

::

    curl http://tabasco.upf.edu/api/sounds/<sound_id>/analysis/tonal/chords_number_rate


**Description**


The Chord Number Rate is the ratio from the number of different chords played more than 1% of the time to the total number of detected chords in "tonal_chord_progression".


**Output**

real, from 0 to 1.


**Application**


Harmonic description and similarity.


**Quality Rating**


Stable


**References**


[1] Chord progression - Wikipedia, the free encyclopedia, http://en.wikipedia.org/wiki/Chord_progression

[2] Circle of fifths - Wikipedia, the free encyclopedia, http://en.wikipedia.org/wiki/Circle_of_fifths




**Distribution Plot**

    .. image:: _static/descriptors/tonal.chords_number_rate.none.png
        :height: 300px


tonal.chords_progression
------------------------

::

    curl http://tabasco.upf.edu/api/sounds/<sound_id>/analysis/tonal/chords_progression


**Description**


A chord is made of three (triad) or more notes that sound simultaneously. Each chord is specified by its root/bass note (what we call "key" A, A#, B, C, C#, D, D#, E, F, F#, G, G#), its type or "mode" (major, minor, major7,...) and its strength (how close the note distribution is from the estimated chord).

The chord is computed using the key estimation algorithm within short segments of 1 or 2 seconds, so that we obtain a succession of chord values.

This succession of chords is called a chord progression.

The Chord Progression is the suite of chords symbols - e.g. C, Am, F#, Bb, Em, G::m, etc - played in the audio piece.



**Output**

string. The string represents the chord sequence of the song, where each chord is one of: A, A#, B, C, C#, D, D#, E, F, F#, G, G#, with an optional m (for minor).


**Application**


Chord estimation, harmonic description, similarity.


**Quality Rating**


Stable


**References**


[1] Gomez, E., "Tonal Description of Polyphonic Audio for Music Content Processing", INFORMS Journal On Computing, Vol. 18, No. 3, Summer 2006, pp. 294-304.

[2] Temperley, D. "Whats key for key? The Krumhansl-Schmuckler key-finding algorithm reconsidered", Music Perception 17(1) pp. 65-100, 1999. http://www.links.cs.cmu.edu/music-analysis/key.html



tonal.chords_scale
------------------

::

    curl http://tabasco.upf.edu/api/sounds/<sound_id>/analysis/tonal/chords_scale


**Description**


A chord is made of three (triad) or more notes that sound simultaneously. Each chord is specified by its root/bass note (what we call "key" A, A#, B, C, C#, D, D#, E, F, F#, G, G#), its type or "mode" (major, minor, major7,...) and its strength (how close the note distribution is from the estimated chord).

A succession of chords is called a chord progression.

The chord is computed using the key estimation algorithm within short segments of 1 or 2 seconds.



**Output**

string. A string representing the mode of the chord of the song. Only triad chords are considered (major, minor)


**Application**


Chord estimation, harmonic description.


**Quality Rating**


Stable


**References**


[1] Gomez, E., "Tonal Description of Polyphonic Audio for Music Content Processing", INFORMS Journal On Computing, Vol. 18, No. 3, Summer 2006, pp. 294-304.

[2] Temperley, D. "Whats key for key? The Krumhansl-Schmuckler key-finding algorithm reconsidered", Music Perception 17(1) pp. 65-100, 1999. http://www.links.cs.cmu.edu/music-analysis/key.html




**Distribution Plot**

    .. image:: _static/descriptors/tonal.chords_scale.none.png
        :height: 300px


tonal.chords_strength
---------------------

::

    curl http://tabasco.upf.edu/api/sounds/<sound_id>/analysis/tonal/chords_strength


**Stats**::

    /dmean
    /dmean2
    /dvar
    /dvar2
    /max
    /mean
    /min
    /var

**Description**


A chord is made of three (triad) or more notes that sound simultaneously. Each chord is specified by its root/bass note (what we call "key" A, A#, B, C, C#, D, D#, E, F, F#, G, G#), its type or "mode" (major, minor, major7,...) and its strength.

The chord is computed using the key estimation algorithm within short segments of 1 or 2 seconds.

The Chord Strength descriptor represents the power/correlation of the chord detection: high value means that the chord detected location is very tonal and low value means that it is not very tonal for the used key profile or template.

A succession of chords is called a chord progression.

The chord is computed using the key estimation algorithm within short segments of 1 or 2 seconds.



**Output**

real, from 0 to 1.


**Application**


Chord estimation, harmonic description, classification.


**Quality Rating**


Stable


**References**


[1] Gomez, E., "Tonal Description of Polyphonic Audio for Music Content Processing", INFORMS Journal On Computing, Vol. 18, No. 3, Summer 2006, pp. 294-304.

[2] Temperley, D. "Whats key for key? The Krumhansl-Schmuckler key-finding algorithm reconsidered", Music Perception 17(1) pp. 65-100, 1999. http://www.links.cs.cmu.edu/music-analysis/key.html




**Distribution Plot**

    .. image:: _static/descriptors/tonal.chords_strength.mean.png
        :height: 300px


tonal.hpcp
----------

::

    curl http://tabasco.upf.edu/api/sounds/<sound_id>/analysis/tonal/hpcp


**Stats**::

    /dmean
    /dmean2
    /dvar
    /dvar2
    /max
    /mean
    /min
    /var

**Description**


The HPCP is the Harmonic Pitch Class Profile, i.e. a 12, 24, 36,... size (size being a multiple of 12) dimensional vector which represents the intensities of each of the frequency bins of an equal-tempered scale.


**Output**

real, from 0 to 1. List of values from 0 to 1.


**Application**


Key estimation, tonal similarity, classification


**Quality Rating**


Stable


**References**


[1] Fujishima, T., "Realtime Chord Recognition of Musical Sound: A System Using Common Lisp Music", ICMC, Beijing, China, 1999, pp. 464-467.

[2] Gomez, E., "Tonal Description of Polyphonic Audio for Music Content Processing", INFORMS Journal On Computing, Vol. 18, No. 3, Summer 2006, pp. 294-304.



tonal.key_key
-------------

::

    curl http://tabasco.upf.edu/api/sounds/<sound_id>/analysis/tonal/key_key


**Description**


In music theory, the key identifies the tonic triad, the chord, major or minor, which represents the final point of rest for a piece, or the focal point of a section. Although the key of a piece may be named in the title (e.g. Symphony in C), or inferred from the key signature, the establishment of key is brought about via functional harmony, a sequence of chords leading to one or more cadences. A key may be major or minor.


**Output**

string. A string representing the key of the song, A, A#, B, C, C#, D, D#, E, F, F#, G, G#


**Application**


Key estimation, tonal similarity, classification


**Quality Rating**


Stable


**References**


[1] Gomez, E., "Tonal Description of Polyphonic Audio for Music Content Processing", INFORMS Journal On Computing, Vol. 18, No. 3, Summer 2006, pp. 294-304.

[2] Temperley, D. "Whats key for key? The Krumhansl-Schmuckler key-finding algorithm reconsidered", Music Perception 17(1) pp. 65-100, 1999. http://www.links.cs.cmu.edu/music-analysis/key.html




**Distribution Plot**

    .. image:: _static/descriptors/tonal.key_key.none.png
        :height: 300px


tonal.key_scale
---------------

::

    curl http://tabasco.upf.edu/api/sounds/<sound_id>/analysis/tonal/key_scale


**Description**


In music theory, the key identifies the tonic triad, the chord, major or minor, which represents the final point of rest for a piece, or the focal point of a section. Although the key of a piece may be named in the title (e.g. Symphony in C), or inferred from the key signature, the establishment of key is brought about via functional harmony, a sequence of chords leading to one or more cadences. A key may be major or minor.


**Output**

string. A string representing the mode of the key of the song, either "major" or "minor"


**Application**


Key estimation, tonal similarity, classification


**Quality Rating**


Stable


**References**


[1] Gomez, E., "Tonal Description of Polyphonic Audio for Music Content Processing", INFORMS Journal On Computing, Vol. 18, No. 3, Summer 2006, pp. 294-304.

[2] Temperley, D. "Whats key for key? The Krumhansl-Schmuckler key-finding algorithm reconsidered", Music Perception 17(1) pp. 65-100, 1999. http://www.links.cs.cmu.edu/music-analysis/key.html




**Distribution Plot**

    .. image:: _static/descriptors/tonal.key_scale.none.png
        :height: 300px


tonal.key_strength
------------------

::

    curl http://tabasco.upf.edu/api/sounds/<sound_id>/analysis/tonal/key_strength


**Description**


The Key Strength descriptor represents the power/correlation of the key: high value means that the piece is very tonal and low value means that it is not very tonal for the used key profile or template.


**Output**

real, from 0 to 1.


**Application**


Tonal similarity, music description, classification between tonal and non-tonal music


**Quality Rating**


Stable


**References**


[1] Gomez, E., "Tonal Description of Polyphonic Audio for Music Content Processing", INFORMS Journal On Computing, Vol. 18, No. 3, Summer 2006, pp. 294-304.

[2] Temperley, D. "Whats key for key? The Krumhansl-Schmuckler key-finding algorithm reconsidered", Music Perception 17(1) pp. 65-100, 1999. http://www.links.cs.cmu.edu/music-analysis/key.html




**Distribution Plot**

    .. image:: _static/descriptors/tonal.key_strength.none.png
        :height: 300px


tonal.thpcp
-----------

::

    curl http://tabasco.upf.edu/api/sounds/<sound_id>/analysis/tonal/thpcp


**Description**


Transposed HPCP, so that the first position corresponds to the highest HPCP magnitude

 * THPCP[n] = HPCP[mod(n-shift), size]

 * n=1, ..., size

   * where size is the size of the HPCP vector (12, 24, 36,...)

   * where shift is the position corresponding to max(HPCP).



**Output**

real, from 0 to 1. The output is a vector of real numbers from 0 to 1.


**Application**


Tonal similarity, scale analysis, western vs non-western music classification, genre classification


**Quality Rating**


Stable


**References**


[1] Fujishima, T., "Realtime Chord Recognition of Musical Sound: A System Using Common Lisp Music", ICMC, Beijing, China, 1999, pp. 464-467.

[2] Gomez, E., "Tonal Description of Polyphonic Audio for Music Content Processing", INFORMS Journal On Computing, Vol. 18, No. 3, Summer 2006, pp. 294-304.



tonal.tuning_diatonic_strength
------------------------------

::

    curl http://tabasco.upf.edu/api/sounds/<sound_id>/analysis/tonal/tuning_diatonic_strength


**Description**


The Diatonic Strength is the "tonal_key_strength" calculated using a diatonic tonal profile on the 120-bins HPCP average.


**Output**

real, from 0 to 1.


**Application**


western vs non-western music classification, key estimation


**Quality Rating**


Stable


**References**


[1] Gomez, E., "Tonal Description of Polyphonic Audio for Music Content Processing", INFORMS Journal On Computing, Vol. 18, No. 3, Summer 2006, pp. 294-304.

[2] Temperley, D. "Whats key for key? The Krumhansl-Schmuckler key-finding algorithm reconsidered", Music Perception 17(1) pp. 65-100, 1999. http://www.links.cs.cmu.edu/music-analysis/key.html




**Distribution Plot**

    .. image:: _static/descriptors/tonal.tuning_diatonic_strength.none.png
        :height: 300px


tonal.tuning_equal_tempered_deviation
-------------------------------------

::

    curl http://tabasco.upf.edu/api/sounds/<sound_id>/analysis/tonal/tuning_equal_tempered_deviation


**Description**


This is a measure of the deviation of the 120-length HPCP (Harmonic Pitch Class Profiles) local maxima with respect to equal-tempered bins. This measure if how the audio piece scale may be considered as an equal-tempered one or not. An Indian music audio piece may have a high equal tempered deviation while a pop song may have a low one.


**Output**

real, non-negative.


**Application**


western vs non-western music classification


**Quality Rating**


Stable


**References**






**Distribution Plot**

    .. image:: _static/descriptors/tonal.tuning_equal_tempered_deviation.none.png
        :height: 300px


tonal.tuning_frequency
----------------------

::

    curl http://tabasco.upf.edu/api/sounds/<sound_id>/analysis/tonal/tuning_frequency


**Description**


Frequency used to tune a piece, by default 440 Hz


**Output**

real, non-negative.


**Application**


Western vs non-western music classification, key estimation, HPCP computation, tonal similarity


**Quality Rating**


Stable


**References**


[1] E. Gomez, Key Estimation from Polyphonic Audio, Music Technology Group, Pompeu Fabra University, 2005



**Distribution Plot**

    .. image:: _static/descriptors/tonal.tuning_frequency.none.png
        :height: 300px


tonal.tuning_nontempered_energy_ratio
-------------------------------------

::

    curl http://tabasco.upf.edu/api/sounds/<sound_id>/analysis/tonal/tuning_nontempered_energy_ratio


**Description**


This is the ratio between the energy on non-tempered peaks and the total energy, computed from the 120-bins HPCP average. This measure if how the audio piece scale may be considered as an equal-tempered one or not. An Indian music audio piece may have a low ratio while a pop song may have a high one.


**Output**

real, from 0 to 1.


**Application**


Western vs non-western music classification


**Quality Rating**


Stable


**References**






**Distribution Plot**

    .. image:: _static/descriptors/tonal.tuning_nontempered_energy_ratio.none.png
        :height: 300px
