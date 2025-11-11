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
size of 1024, while for the tonal namespace the frame size is 4096 and the hop size 2048.


Glossary 
>>>>>>>>>>>>>>>>

Basic terms used in the documentation of audio descriptors:

========= =====================================
numeric   The descriptor returns a numeric value; can be either an integer or a float.
integer   The descriptor returns an integer value only.
string    The descriptor returns a textual value.
boolean   The descriptor returns a binary value; 0 (no) or 1 (yes).
array[x]  The descriptor returns a list of elements of type X.
VL        Variable-length descriptor; the returned list may vary in length depending on the sound.
mean      The arithmetic mean of the descriptor values over the entire sound.
min       The lowest (minimum) descriptor value over the entire sound.
max       The highest (maximum) descriptor value over the entire sound.
var       The variance of the descriptor values over the entire sound.
========= =====================================

If ``Mode`` ends with a number in parentheses (``X``), it indicates that this mode is calculated for a specific number of values.  
For example, if ``Mode`` is ``mean (36)``, it represents the mean calculated across 36 values.

.. All single-value descriptors with type string or single numeric value can be used for filtering. 


Descriptors (main)
>>>>>>>>>>>>>>>>

beat_count
-------------------------

::

    curl https://freesound.org/api/sounds/<sound_id>/analysis/beat_count

**Description:** Number of beats in the audio signal, derived from the total detected beat positions and expresses a measure of rhythmic density or tempo-related activity.

**Type:** integer

**More information:** http://essentia.upf.edu/documentation/reference/streaming_RhythmExtractor2013.html

**Distribution in Freesound**

    .. image:: _static/descriptors/beat_count.png
        :height: 300px


beat_loudness
-------------------------

::

    curl https://freesound.org/api/sounds/<sound_id>/analysis/beat_loudness

**Description:** Spectral energy measured at the beat positions of the audio signal.

**Mode:** mean

**Type:** numeric

**More information:** https://essentia.upf.edu/reference/streaming_BeatsLoudness.html

**Distribution in Freesound**

    .. image:: _static/descriptors/beat_loudness.png
        :height: 300px


beat_times
-------------------------

::

    curl https://freesound.org/api/sounds/<sound_id>/analysis/beat_times

**Description:** Beat timestamps (in seconds) for the audio signal, which can vary according to the amount (count) of beats identified in the audio.

**Mode:** VL

**Type:** array[numeric]

**More information:** http://essentia.upf.edu/documentation/reference/streaming_RhythmExtractor2013.html

**Distribution in Freesound**

    .. image:: _static/descriptors/beat_times.png
        :height: 300px


boominess
-------------------------

::

    curl https://freesound.org/api/sounds/<sound_id>/analysis/boominess

**Description:** Boominess of the audio signal. A boomy sound is one that conveys a sense of loudness, depth and resonance.

**Type:** numeric

**Values:** 0-100

**Distribution in Freesound**

    .. image:: _static/descriptors/boominess.png
        :height: 300px


bpm
-------------------------

::

    curl https://freesound.org/api/sounds/<sound_id>/analysis/bpm

**Description:** BPM value estimated by beat tracking algorithm.

**Type:** integer

**More information:** https://en.wikipedia.org/wiki/Tempo

**Distribution in Freesound**

    .. image:: _static/descriptors/bpm.png
        :height: 300px


bpm_confidence
-------------------------

::

    curl https://freesound.org/api/sounds/<sound_id>/analysis/bpm_confidence

**Description:** Confidence score on how reliable the tempo (BPM) estimation is.

**Type:** numeric

**Values:** 0-1

**Distribution in Freesound**

    .. image:: _static/descriptors/bpm_confidence.png
        :height: 300px


brightness
-------------------------

::

    curl https://freesound.org/api/sounds/<sound_id>/analysis/brightness

**Description:** Brightness of the audio signal. A bright sound is one that is clear/vibrant and/or contains significant high-pitched elements.

**Type:** numeric

**Values:** 0-100

**Distribution in Freesound**

    .. image:: _static/descriptors/brightness.png
        :height: 300px


depth
-------------------------

::

    curl https://freesound.org/api/sounds/<sound_id>/analysis/depth

**Description:** Depth of the audio signal. A deep sound is one that conveys the sense of having been made far down below the surface of its source.

**Type:** numeric

**Values:** 0-100

**Distribution in Freesound**

    .. image:: _static/descriptors/depth.png
        :height: 300px


dissonance
-------------------------

::

    curl https://freesound.org/api/sounds/<sound_id>/analysis/dissonance

**Description:** Sensory dissonance of the audio signal given its spectral peaks.

**Mode:** mean

**Type:** numeric

**More information:** http://essentia.upf.edu/documentation/reference/streaming_Dissonance.html

**Distribution in Freesound**

    .. image:: _static/descriptors/dissonance.png
        :height: 300px


duration
-------------------------

::

    curl https://freesound.org/api/sounds/<sound_id>/analysis/duration

**Description:** Total duration of the audio signal in seconds.

**Type:** numeric

**More information:** https://essentia.upf.edu/reference/streaming_Duration.html

**Distribution in Freesound**

    .. image:: _static/descriptors/duration.png
        :height: 300px


duration_effective
-------------------------

::

    curl https://freesound.org/api/sounds/<sound_id>/analysis/duration_effective

**Description:** Duration of the audio signal (in seconds) during which the envelope amplitude is perceptually significant (above 40% of peak and ?90?dB), e.g. for distinguishing short/percussive from sustained sounds.

**Type:** numeric

**More information:** https://essentia.upf.edu/reference/streaming_EffectiveDuration.html

**Distribution in Freesound**

    .. image:: _static/descriptors/duration_effective.png
        :height: 300px


dynamic_range
-------------------------

::

    curl https://freesound.org/api/sounds/<sound_id>/analysis/dynamic_range

**Description:** Loudness range (dB, LU) of the audio signal measured using the EBU R128 standard.

**Type:** numeric

**Distribution in Freesound**

    .. image:: _static/descriptors/dynamic_range.png
        :height: 300px


hardness
-------------------------

::

    curl https://freesound.org/api/sounds/<sound_id>/analysis/hardness

**Description:** Hardness of the audio signal. A hard sound is one that conveys the sense of having been made (i) by something solid, firm or rigid; or (ii) with a great deal of force.

**Mode:** mean

**Type:** numeric

**Values:** 0-100

**Distribution in Freesound**

    .. image:: _static/descriptors/hardness.png
        :height: 300px


inharmonicity
-------------------------

::

    curl https://freesound.org/api/sounds/<sound_id>/analysis/inharmonicity

**Description:** Deviation of spectral components from perfect harmonicity, computed as the energy-weighted divergence from their closest multiples of the fundamental frequency.

**Mode:** mean

**Type:** numeric

**Values:** 0-1

**More information:** https://essentia.upf.edu/reference/streaming_Inharmonicity.html

**Distribution in Freesound**

    .. image:: _static/descriptors/inharmonicity.png
        :height: 300px


loopable
-------------------------

::

    curl https://freesound.org/api/sounds/<sound_id>/analysis/loopable

**Description:** Whether the audio signal is loopable, i.e. it begins and ends in a way that sounds smooth when repeated.

**Type:** boolean

**More information:** https://en.wikipedia.org/wiki/Loop_(music)

**Distribution in Freesound**

    .. image:: _static/descriptors/loopable.png
        :height: 300px


loudness
-------------------------

::

    curl https://freesound.org/api/sounds/<sound_id>/analysis/loudness

**Description:** Overall loudness (LUFS) of the audio signal measured using the EBU R128 standard.

**Type:** numeric

**More information:** https://en.wikipedia.org/wiki/LUFS

**Distribution in Freesound**

    .. image:: _static/descriptors/loudness.png
        :height: 300px


note_confidence
-------------------------

::

    curl https://freesound.org/api/sounds/<sound_id>/analysis/note_confidence

**Description:** Confidence score on how reliable the note name/MIDI estimation is.

**Type:** numeric

**Values:** 0-1

**Distribution in Freesound**

    .. image:: _static/descriptors/note_confidence.png
        :height: 300px


note_midi
-------------------------

::

    curl https://freesound.org/api/sounds/<sound_id>/analysis/note_midi

**Description:** MIDI value corresponding to the estimated note (computed by the note_name descriptor).

**Type:** integer

**Distribution in Freesound**

    .. image:: _static/descriptors/note_midi.png
        :height: 300px


note_name
-------------------------

::

    curl https://freesound.org/api/sounds/<sound_id>/analysis/note_name

**Description:** Pitch note name that includes one of the 12 western notes ["A", "A#", "B", "C", "C#", "D", "D#", "E", "F", "F#", "G", "G#"] and the octave number, e.g. "A4", "E#7". It is computed by the median of the estimated fundamental frequency.

**Type:** string

**Distribution in Freesound**

    .. image:: _static/descriptors/note_name.png
        :height: 300px


onset_count
-------------------------

::

    curl https://freesound.org/api/sounds/<sound_id>/analysis/onset_count

**Description:** Number of detected onsets in the audio signal.

**Type:** integer

**More information:** http://essentia.upf.edu/documentation/reference/streaming_OnsetRate.html

**Distribution in Freesound**

    .. image:: _static/descriptors/onset_count.png
        :height: 300px


onset_times
-------------------------

::

    curl https://freesound.org/api/sounds/<sound_id>/analysis/onset_times

**Description:** Timestamps for the detected onsets in the audio signal in seconds, which can vary according to the amount of onsets (computed by the onset_count descriptor).

**Mode:** VL

**Type:** array[numeric]

**More information:** http://essentia.upf.edu/documentation/reference/streaming_OnsetRate.html

**Distribution in Freesound**

    .. image:: _static/descriptors/onset_times.png
        :height: 300px


pitch
-------------------------

::

    curl https://freesound.org/api/sounds/<sound_id>/analysis/pitch

**Description:** Mean (average) fundamental frequency derived from the audio signal, computed with the YinFFT algorithm.

**Mode:** mean

**Type:** numeric

**Values:** 0-25000

**More information:** http://essentia.upf.edu/documentation/reference/streaming_PitchYinFFT.html

**Distribution in Freesound**

    .. image:: _static/descriptors/pitch.png
        :height: 300px


pitch_salience
-------------------------

::

    curl https://freesound.org/api/sounds/<sound_id>/analysis/pitch_salience

**Description:** Pitch salience (i.e. tone sensation) given by the ratio of the highest auto correlation value of the spectrum to the non-shifted auto correlation value. Unpitched sounds and pure tones have value close to 0.

**Mode:** mean

**Type:** numeric

**Values:** 0-1

**More information:** http://essentia.upf.edu/documentation/reference/streaming_PitchYinFFT.html

**Distribution in Freesound**

    .. image:: _static/descriptors/pitch_salience.png
        :height: 300px


reverbness
-------------------------

::

    curl https://freesound.org/api/sounds/<sound_id>/analysis/reverbness

**Description:** Whether the signal is reverberated or not.

**Type:** boolean

**More information:** https://en.wikipedia.org/wiki/Reverberation

**Distribution in Freesound**

    .. image:: _static/descriptors/reverbness.png
        :height: 300px


roughness
-------------------------

::

    curl https://freesound.org/api/sounds/<sound_id>/analysis/roughness

**Description:** Roughness of the audio signal. A rough sound is one that has an uneven or irregular sonic texture.

**Type:** numeric

**Values:** 0-100

**Distribution in Freesound**

    .. image:: _static/descriptors/roughness.png
        :height: 300px


sharpness
-------------------------

::

    curl https://freesound.org/api/sounds/<sound_id>/analysis/sharpness

**Description:** Sharpness of the audio signal. A sharp sound is one that suggests it might cut if it were to take on physical form.

**Type:** numeric

**Values:** 0-100

**Distribution in Freesound**

    .. image:: _static/descriptors/sharpness.png
        :height: 300px


silence_rate
-------------------------

::

    curl https://freesound.org/api/sounds/<sound_id>/analysis/silence_rate

**Description:** Amount of silence in the audio signal, computed by the fraction of frames with instant power below ?30?dB.

**Mode:** mean

**Type:** numeric

**Values:** 0-1

**More information:** http://essentia.upf.edu/documentation/reference/streaming_SilenceRate.html

**Distribution in Freesound**

    .. image:: _static/descriptors/silence_rate.png
        :height: 300px


single_event
-------------------------

::

    curl https://freesound.org/api/sounds/<sound_id>/analysis/single_event

**Description:** Whether the audio signal contains one single audio event or more than one. This computation is based on the loudness of the signal and does not do any frequency analysis.

**Type:** boolean

**Distribution in Freesound**

    .. image:: _static/descriptors/single_event.png
        :height: 300px


start_time
-------------------------

::

    curl https://freesound.org/api/sounds/<sound_id>/analysis/start_time

**Description:** The moment at which sound begins in seconds, i.e. when the audio signal first rises above silence.

**Type:** numeric

**More information:** https://essentia.upf.edu/reference/streaming_StartStopSilence.html

**Distribution in Freesound**

    .. image:: _static/descriptors/start_time.png
        :height: 300px


tonality
-------------------------

::

    curl https://freesound.org/api/sounds/<sound_id>/analysis/tonality

**Description:** Key (tonality) estimated by a key detection algorithm. The key name includes the root note of the scale, which is one of ["A", "A#", "B", "C", "C#", "D", "D#", "E", "F", "F#", "G", "G#"], and the scale mode, which is one of ["major", "minor"], e.g. "C minor", "F# major".

**Type:** string

**More information:** https://en.wikipedia.org/wiki/Key_(music)

**Distribution in Freesound**

    .. image:: _static/descriptors/tonality.png
        :height: 300px


tonality_confidence
-------------------------

::

    curl https://freesound.org/api/sounds/<sound_id>/analysis/tonality_confidence

**Description:** Confidence score on how reliable the key estimation is (computed by the tonality descriptor).

**Type:** numeric

**Values:** 0-1

**Distribution in Freesound**

    .. image:: _static/descriptors/tonality_confidence.png
        :height: 300px


warmth
-------------------------

::

    curl https://freesound.org/api/sounds/<sound_id>/analysis/warmth

**Description:** Warmth of the audio signal. A warm sound is one that promotes a sensation analogous to that caused by a physical increase in temperature.

**Type:** numeric

**Values:** 0-100

**Distribution in Freesound**

    .. image:: _static/descriptors/warmth.png
        :height: 300px


Descriptors (advanced)
>>>>>>>>>>>>>>>>

amplitude_peak_ratio
-------------------------

::

    curl https://freesound.org/api/sounds/<sound_id>/analysis/amplitude_peak_ratio

**Description:** Ratio between the position of the peak in the amplitude envelope and the total envelope duration, indicating whether the maximum magnitude of the audio signal occurs early (impulsive or decrescendo) or late (crescendo).

**Type:** numeric

**Values:** 0-1

**More information:** http://essentia.upf.edu/documentation/reference/streaming_MaxToTotal.html

**Distribution in Freesound**

    .. image:: _static/descriptors/amplitude_peak_ratio.png
        :height: 300px


chord_count
-------------------------

::

    curl https://freesound.org/api/sounds/<sound_id>/analysis/chord_count

**Description:** Number of chords in the audio signal based on the number of detected chords by the chord_progression descriptor.

**Type:** integer

**More information:** http://essentia.upf.edu/documentation/reference/streaming_ChordsDescriptors.html

**Distribution in Freesound**

    .. image:: _static/descriptors/chord_count.png
        :height: 300px


chord_progression
-------------------------

::

    curl https://freesound.org/api/sounds/<sound_id>/analysis/chord_progression

**Description:** Chords estimated from the harmonic pitch class profiles (HPCPs) across the audio signal. Using the pitch classes ["A", "A#", "B", "C", "C#", "D", "D#", "E", "F", "F#", "G", "G#"], it finds the best-matching major or minor triad and outputs a time-varying chord sequence as a sequence of labels (e.g. A#, Bm). Note, chords are major if no minor symbol.

**Mode:** VL

**Type:** array[string]

**More information:** http://essentia.upf.edu/documentation/reference/streaming_ChordsDetection.html

**Distribution in Freesound**

    .. image:: _static/descriptors/chord_progression.png
        :height: 300px


decay_strength
-------------------------

::

    curl https://freesound.org/api/sounds/<sound_id>/analysis/decay_strength

**Description:** Rate at which the audio signal's energy decays (i.e. how quickly it decreases) after the initial attack. It is computed from a non-linear combination of the signal's energy and its temporal centroid (the balance point of the signal's absolute amplitude).

**Type:** numeric

**More information:** https://essentia.upf.edu/reference/streaming_StrongDecay.html

**Distribution in Freesound**

    .. image:: _static/descriptors/decay_strength.png
        :height: 300px


hpcp
-------------------------

::

    curl https://freesound.org/api/sounds/<sound_id>/analysis/hpcp

**Description:** Harmonic Pitch Class Profile (HPCP) computed from the spectral peaks of the audio signal, representing the energy distribution across 36 pitch classes (3 subdivisions per semitone).

**Mode:** mean (36)

**Type:** array[numeric]

**Values:** 0-36

**More information:** http://essentia.upf.edu/documentation/reference/streaming_HPCP.html, https://en.wikipedia.org/wiki/Harmonic_pitch_class_profiles

**Distribution in Freesound**

    .. image:: _static/descriptors/hpcp.png
        :height: 300px


hpcp_crest
-------------------------

::

    curl https://freesound.org/api/sounds/<sound_id>/analysis/hpcp_crest

**Description:** Dominance of the strongest pitch class (crest) compared to the rest, computed as the ratio between the maximum HPCP value and the mean HPCP value (computed by the hpcp descriptor).

**Mode:** mean

**Type:** numeric

**More information:** https://essentia.upf.edu/reference/streaming_Crest.html

**Distribution in Freesound**

    .. image:: _static/descriptors/hpcp_crest.png
        :height: 300px


hpcp_entropy
-------------------------

::

    curl https://freesound.org/api/sounds/<sound_id>/analysis/hpcp_entropy

**Description:** Uniformity of the pitch-class distribution, computed as the Shannon entropy of the HPCP (computed by the hpcp descriptor).

**Mode:** mean

**Type:** numeric

**More information:** http://essentia.upf.edu/documentation/reference/streaming_Entropy.html, http://essentia.upf.edu/documentation/reference/streaming_HPCP.html

**Distribution in Freesound**

    .. image:: _static/descriptors/hpcp_entropy.png
        :height: 300px


log_attack_time
-------------------------

::

    curl https://freesound.org/api/sounds/<sound_id>/analysis/log_attack_time

**Description:** Log (base 10) of the attack time of the audio signal's envelope, where the attack time is defined as the time duration from when the sound becomes perceptually audible to when it reaches its maximum intensity.

**Type:** numeric

**More information:** https://essentia.upf.edu/reference/streaming_LogAttackTime.html

**Distribution in Freesound**

    .. image:: _static/descriptors/log_attack_time.png
        :height: 300px


mfcc
-------------------------

::

    curl https://freesound.org/api/sounds/<sound_id>/analysis/mfcc

**Description:** 13 mel-frequency cepstrum coefficients of a spectrum (MFCC-FB40).

**Mode:** mean (13)

**Type:** array[numeric]

**More information:** https://essentia.upf.edu/reference/streaming_MFCC.html

**Distribution in Freesound**

    .. image:: _static/descriptors/mfcc.png
        :height: 300px


pitch_max
-------------------------

::

    curl https://freesound.org/api/sounds/<sound_id>/analysis/pitch_max

**Description:** Maximum fundamental frequency observed throughout the audio signal.

**Mode:** max

**Type:** numeric

**More information:** http://essentia.upf.edu/documentation/reference/streaming_PitchYinFFT.html

**Distribution in Freesound**

    .. image:: _static/descriptors/pitch_max.png
        :height: 300px


pitch_min
-------------------------

::

    curl https://freesound.org/api/sounds/<sound_id>/analysis/pitch_min

**Description:** Minimum fundamental frequency observed throughout the audio signal.

**Mode:** min

**Type:** numeric

**More information:** http://essentia.upf.edu/documentation/reference/streaming_PitchYinFFT.html

**Distribution in Freesound**

    .. image:: _static/descriptors/pitch_min.png
        :height: 300px


pitch_var
-------------------------

::

    curl https://freesound.org/api/sounds/<sound_id>/analysis/pitch_var

**Description:** Variance of the fundamental frequency of the audio signal.

**Mode:** var

**Type:** numeric

**More information:** http://essentia.upf.edu/documentation/reference/streaming_PitchYinFFT.html

**Distribution in Freesound**

    .. image:: _static/descriptors/pitch_var.png
        :height: 300px


spectral_centroid
-------------------------

::

    curl https://freesound.org/api/sounds/<sound_id>/analysis/spectral_centroid

**Description:** Spectral centroid of the audio signal, indicating where the "center of mass" of the spectrum is. It correlates with the perception of "brightness" of a sound, making it useful for characterizing musical timbre. It is computed as the weighted mean of the signal's frequencies, weighted by their magnitudes.

**Mode:** mean

**Type:** numeric

**More information:** http://essentia.upf.edu/documentation/reference/streaming_Centroid.html, https://en.wikipedia.org/wiki/Spectral_centroid

**Distribution in Freesound**

    .. image:: _static/descriptors/spectral_centroid.png
        :height: 300px


spectral_complexity
-------------------------

::

    curl https://freesound.org/api/sounds/<sound_id>/analysis/spectral_complexity

**Description:** Spectral complexity of the audio signal's spectrum, based on the number of peaks in the spectrum.

**Mode:** mean

**Type:** numeric

**More information:** http://essentia.upf.edu/documentation/reference/streaming_SpectralComplexity.html

**Distribution in Freesound**

    .. image:: _static/descriptors/spectral_complexity.png
        :height: 300px


spectral_crest
-------------------------

::

    curl https://freesound.org/api/sounds/<sound_id>/analysis/spectral_crest

**Description:** Dominance of the strongest spectral peak (crest) compared to the rest, computed as the ratio between the maximum and mean spectral magnitudes.

**Mode:** mean

**Type:** numeric

**More information:** http://essentia.upf.edu/documentation/reference/streaming_Crest.html

**Distribution in Freesound**

    .. image:: _static/descriptors/spectral_crest.png
        :height: 300px


spectral_energy
-------------------------

::

    curl https://freesound.org/api/sounds/<sound_id>/analysis/spectral_energy

**Description:** Energy in the spectrum of the audio signal. It represents the total magnitude of all frequency components and indicates how much power is present across the spectrum.

**Mode:** mean

**Type:** numeric

**More information:** http://essentia.upf.edu/documentation/reference/streaming_Energy.html

**Distribution in Freesound**

    .. image:: _static/descriptors/spectral_energy.png
        :height: 300px


spectral_entropy
-------------------------

::

    curl https://freesound.org/api/sounds/<sound_id>/analysis/spectral_entropy

**Description:** Shannon entropy in the frequency domain of the audio signal, measuring the unpredictability in the spectrum.

**Mode:** mean

**Type:** numeric

**More information:** http://essentia.upf.edu/documentation/reference/streaming_Entropy.html

**Distribution in Freesound**

    .. image:: _static/descriptors/spectral_entropy.png
        :height: 300px


spectral_flatness
-------------------------

::

    curl https://freesound.org/api/sounds/<sound_id>/analysis/spectral_flatness

**Description:** Flatness of the spectrum measured as the ratio of its geometric mean to its arithmetic mean (in dB). High values indicate a noise-like, flat spectrum with evenly distributed power, while low values indicate a tone-like, spiky spectrum with power concentrated in a few frequency bands.

**Mode:** mean

**Type:** numeric

**Values:** 0-1

**More information:** http://essentia.upf.edu/documentation/reference/streaming_FlatnessDB.html

**Distribution in Freesound**

    .. image:: _static/descriptors/spectral_flatness.png
        :height: 300px


spectral_rolloff
-------------------------

::

    curl https://freesound.org/api/sounds/<sound_id>/analysis/spectral_rolloff

**Description:** Roll-off frequency of the spectrum, defined as the frequency under which some percentage (cutoff) of the total energy of the spectrum is contained. It can be used to distinguish between harmonic (below roll-off) and noisy sounds (above roll-off).

**Mode:** mean

**Type:** numeric

**Values:** 0-25000

**More information:** http://essentia.upf.edu/documentation/reference/streaming_RollOff.html

**Distribution in Freesound**

    .. image:: _static/descriptors/spectral_rolloff.png
        :height: 300px


spectral_skewness
-------------------------

::

    curl https://freesound.org/api/sounds/<sound_id>/analysis/spectral_skewness

**Description:** Skewness of the spectrum given its central moments. It measures how the values of the spectrum are dispersed around the mean and is a key indicator of the distribution's shape.

**Mode:** mean

**Type:** numeric

**More information:** https://essentia.upf.edu/reference/streaming_CentralMoments.html

**Distribution in Freesound**

    .. image:: _static/descriptors/spectral_skewness.png
        :height: 300px


spectral_spread
-------------------------

::

    curl https://freesound.org/api/sounds/<sound_id>/analysis/spectral_spread

**Description:** Spread (variance) of the spectrum given its central moments. It measures how the values of the spectrum are dispersed around the mean and is a key indicator of the distribution's shape.

**Mode:** mean

**Type:** numeric

**More information:** https://essentia.upf.edu/reference/streaming_CentralMoments.html

**Distribution in Freesound**

    .. image:: _static/descriptors/spectral_spread.png
        :height: 300px


temporal_centroid
-------------------------

::

    curl https://freesound.org/api/sounds/<sound_id>/analysis/temporal_centroid

**Description:** Temporal centroid of the audio signal, defined as the time point at which the temporal balancing position of the sound event energy.

**Type:** numeric

**Values:** 0-1

**More information:** http://essentia.upf.edu/documentation/reference/streaming_Centroid.html

**Distribution in Freesound**

    .. image:: _static/descriptors/temporal_centroid.png
        :height: 300px


temporal_centroid_ratio
-------------------------

::

    curl https://freesound.org/api/sounds/<sound_id>/analysis/temporal_centroid_ratio

**Description:** Ratio of the temporal centroid to the total length of the audio signal's envelope, which shows how the sound is �balanced'. Values close to 0 indicate most of the energy is concentrated early (decrescendo or impulsive), while values close to 1 indicate energy concentrated late (crescendo).

**Type:** numeric

**More information:** http://essentia.upf.edu/documentation/reference/streaming_TCToTotal.html

**Distribution in Freesound**

    .. image:: _static/descriptors/temporal_centroid_ratio.png
        :height: 300px


temporal_decrease
-------------------------

::

    curl https://freesound.org/api/sounds/<sound_id>/analysis/temporal_decrease

**Description:** Overall decrease of the audio signal's amplitude over time, computed as the linear regression coefficient.

**Mode:** mean

**Type:** numeric

**More information:** http://essentia.upf.edu/documentation/reference/streaming_Decrease.html

**Distribution in Freesound**

    .. image:: _static/descriptors/temporal_decrease.png
        :height: 300px


temporal_skewness
-------------------------

::

    curl https://freesound.org/api/sounds/<sound_id>/analysis/temporal_skewness

**Description:** Skewness of the audio signal in the time domain given its central moments. It measures how the amplitude values of the signal are dispersed around the mean and is a key indicator of the distribution's shape.

**Mode:** mean

**Type:** numeric

**More information:** https://essentia.upf.edu/reference/streaming_CentralMoments.html

**Distribution in Freesound**

    .. image:: _static/descriptors/temporal_skewness.png
        :height: 300px


temporal_spread
-------------------------

::

    curl https://freesound.org/api/sounds/<sound_id>/analysis/temporal_spread

**Description:** Spread (variance) of the audio signal in the time domain given its central moments. It measures how the amplitude values of the signal are dispersed around the mean and is a key indicator of the distribution's shape.

**Mode:** mean

**Type:** numeric

**More information:** https://essentia.upf.edu/reference/streaming_CentralMoments.html

**Distribution in Freesound**

    .. image:: _static/descriptors/temporal_spread.png
        :height: 300px


tristimulus
-------------------------

::

    curl https://freesound.org/api/sounds/<sound_id>/analysis/tristimulus

**Description:** Tristimulus of the audio signal given its harmonic peaks. It measures the relative contribution of harmonic groups in a signal's spectrum, where the first value captures the first harmonic, the second captures harmonics 2-4, and the third captures all remaining harmonics. It is a timbre equivalent to the color attributes in the vision.

**Mode:** mean (3)

**Type:** array[numeric]

**More information:** https://essentia.upf.edu/reference/streaming_Tristimulus.html

**Distribution in Freesound**

    .. image:: _static/descriptors/tristimulus.png
        :height: 300px


zero_crossing_rate
-------------------------

::

    curl https://freesound.org/api/sounds/<sound_id>/analysis/zero_crossing_rate

**Description:** Zero-crossing rate of the audio signal. It is the number of sign changes between consecutive samples divided by the total number of samples. Noisy signals tend to have a higher value. For monophonic tonal signals, it can be used as a primitive pitch detection algorithm.

**Mode:** mean

**Type:** numeric

**Values:** 0-1

**More information:** http://essentia.upf.edu/documentation/reference/streaming_ZeroCrossingRate.html

**Distribution in Freesound**

    .. image:: _static/descriptors/zero_crossing_rate.png
        :height: 300px


