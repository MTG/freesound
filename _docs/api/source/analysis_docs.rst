
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

    curl http://www.freesound.org/api/sounds/<sound_id>/analysis/metadata/audio_properties


**Stats**::


/equal_loudness



metadata.version
-------------------------

::

    curl http://www.freesound.org/api/sounds/<sound_id>/analysis/metadata/version


**Stats**::


/essentia



Lowlevel Descriptors
>>>>>>>>>>>>>>>>>>>>


lowlevel.spectral_complexity
-------------------------

::

    curl http://www.freesound.org/api/sounds/<sound_id>/analysis/lowlevel/spectral_complexity

**Essentia Algorithm**

http://essentia.upf.edu/documentation/reference/streaming_SpectralComplexity.html


**Stats**::


/min
/max
/dvar2
/dmean2
/dmean
/var
/dvar
/mean


**Distribution in Freesound**

    .. image:: _static/descriptors/lowlevel.spectral_complexity.mean.png
        :height: 300px



lowlevel.silence_rate_20dB
-------------------------

::

    curl http://www.freesound.org/api/sounds/<sound_id>/analysis/lowlevel/silence_rate_20dB

**Essentia Algorithm**

http://essentia.upf.edu/documentation/reference/streaming_SilenceRate.html


**Stats**::


/min
/max
/dvar2
/dmean2
/dmean
/var
/dvar
/mean


**Distribution in Freesound**




lowlevel.average_loudness
-------------------------

::

    curl http://www.freesound.org/api/sounds/<sound_id>/analysis/lowlevel/average_loudness

**Essentia Algorithm**

http://essentia.upf.edu/documentation/reference/streaming_Loudness		.html



lowlevel.pitch
-------------------------

::

    curl http://www.freesound.org/api/sounds/<sound_id>/analysis/lowlevel/pitch

**Essentia Algorithm**

http://essentia.upf.edu/documentation/reference/streaming_PitchYinFFT.html


**Stats**::


/min
/max
/dvar2
/dmean2
/dmean
/var
/dvar
/mean


**Distribution in Freesound**

    .. image:: _static/descriptors/lowlevel.pitch.mean.png
        :height: 300px



lowlevel.spectral_kurtosis
-------------------------

::

    curl http://www.freesound.org/api/sounds/<sound_id>/analysis/lowlevel/spectral_kurtosis

**Essentia Algorithm**

http://essentia.upf.edu/documentation/reference/streaming_CentralMoments.html


**Stats**::


/min
/max
/dvar2
/dmean2
/dmean
/var
/dvar
/mean


**Distribution in Freesound**

    .. image:: _static/descriptors/lowlevel.spectral_kurtosis.mean.png
        :height: 300px



lowlevel.barkbands_kurtosis
-------------------------

::

    curl http://www.freesound.org/api/sounds/<sound_id>/analysis/lowlevel/barkbands_kurtosis

**Essentia Algorithm**

http://essentia.upf.edu/documentation/reference/streaming_CentralMoments.html


**Stats**::


/min
/max
/dvar2
/dmean2
/dmean
/var
/dvar
/mean


**Distribution in Freesound**

    .. image:: _static/descriptors/lowlevel.barkbands_kurtosis.mean.png
        :height: 300px



lowlevel.scvalleys
-------------------------

::

    curl http://www.freesound.org/api/sounds/<sound_id>/analysis/lowlevel/scvalleys

**Essentia Algorithm**

http://essentia.upf.edu/documentation/reference/streaming_SpectralContrast.html


**Stats**::


/min
/max
/dvar2
/dmean2
/dmean
/var
/dvar
/mean


**Distribution in Freesound**

    .. image:: _static/descriptors/lowlevel.scvalleys.mean.000.png
        :height: 300px
    .. image:: _static/descriptors/lowlevel.scvalleys.mean.001.png
        :height: 300px
    .. image:: _static/descriptors/lowlevel.scvalleys.mean.002.png
        :height: 300px
    .. image:: _static/descriptors/lowlevel.scvalleys.mean.003.png
        :height: 300px
    .. image:: _static/descriptors/lowlevel.scvalleys.mean.004.png
        :height: 300px
    .. image:: _static/descriptors/lowlevel.scvalleys.mean.005.png
        :height: 300px



lowlevel.spectral_spread
-------------------------

::

    curl http://www.freesound.org/api/sounds/<sound_id>/analysis/lowlevel/spectral_spread

**Essentia Algorithm**

http://essentia.upf.edu/documentation/reference/streaming_CentralMoments.html


**Stats**::


/min
/max
/dvar2
/dmean2
/dmean
/var
/dvar
/mean


**Distribution in Freesound**




lowlevel.spectral_rms
-------------------------

::

    curl http://www.freesound.org/api/sounds/<sound_id>/analysis/lowlevel/spectral_rms

**Essentia Algorithm**

http://essentia.upf.edu/documentation/reference/streaming_RMS.html


**Stats**::


/min
/max
/dvar2
/dmean2
/dmean
/var
/dvar
/mean


**Distribution in Freesound**

    .. image:: _static/descriptors/lowlevel.spectral_rms.mean.png
        :height: 300px



lowlevel.dissonance
-------------------------

::

    curl http://www.freesound.org/api/sounds/<sound_id>/analysis/lowlevel/dissonance

**Essentia Algorithm**

http://essentia.upf.edu/documentation/reference/streaming_Dissonance.html


**Stats**::


/min
/max
/dvar2
/dmean2
/dmean
/var
/dvar
/mean


**Distribution in Freesound**

    .. image:: _static/descriptors/lowlevel.dissonance.mean.png
        :height: 300px



lowlevel.spectral_energyband_high
-------------------------

::

    curl http://www.freesound.org/api/sounds/<sound_id>/analysis/lowlevel/spectral_energyband_high

**Essentia Algorithm**

http://essentia.upf.edu/documentation/reference/streaming_EnergyBand.html


**Stats**::


/min
/max
/dvar2
/dmean2
/dmean
/var
/dvar
/mean


**Distribution in Freesound**

    .. image:: _static/descriptors/lowlevel.spectral_energyband_high.mean.png
        :height: 300px



lowlevel.spectral_skewness
-------------------------

::

    curl http://www.freesound.org/api/sounds/<sound_id>/analysis/lowlevel/spectral_skewness

**Essentia Algorithm**

http://essentia.upf.edu/documentation/reference/streaming_CentralMoments.html


**Stats**::


/min
/max
/dvar2
/dmean2
/dmean
/var
/dvar
/mean


**Distribution in Freesound**

    .. image:: _static/descriptors/lowlevel.spectral_skewness.mean.png
        :height: 300px



lowlevel.spectral_flux
-------------------------

::

    curl http://www.freesound.org/api/sounds/<sound_id>/analysis/lowlevel/spectral_flux

**Essentia Algorithm**

http://essentia.upf.edu/documentation/reference/streaming_Flux.html


**Stats**::


/min
/max
/dvar2
/dmean2
/dmean
/var
/dvar
/mean


**Distribution in Freesound**

    .. image:: _static/descriptors/lowlevel.spectral_flux.mean.png
        :height: 300px



lowlevel.silence_rate_30dB
-------------------------

::

    curl http://www.freesound.org/api/sounds/<sound_id>/analysis/lowlevel/silence_rate_30dB

**Essentia Algorithm**

http://essentia.upf.edu/documentation/reference/streaming_SilenceRate.html


**Stats**::


/min
/max
/dvar2
/dmean2
/dmean
/var
/dvar
/mean


**Distribution in Freesound**




lowlevel.spectral_contrast
-------------------------

::

    curl http://www.freesound.org/api/sounds/<sound_id>/analysis/lowlevel/spectral_contrast

**Essentia Algorithm**

http://essentia.upf.edu/documentation/reference/streaming_SpectralContrast.html


**Stats**::


/min
/max
/dvar2
/dmean2
/dmean
/var
/dvar
/mean


**Distribution in Freesound**

    .. image:: _static/descriptors/lowlevel.spectral_contrast.mean.000.png
        :height: 300px
    .. image:: _static/descriptors/lowlevel.spectral_contrast.mean.001.png
        :height: 300px
    .. image:: _static/descriptors/lowlevel.spectral_contrast.mean.002.png
        :height: 300px
    .. image:: _static/descriptors/lowlevel.spectral_contrast.mean.003.png
        :height: 300px
    .. image:: _static/descriptors/lowlevel.spectral_contrast.mean.004.png
        :height: 300px
    .. image:: _static/descriptors/lowlevel.spectral_contrast.mean.005.png
        :height: 300px



lowlevel.spectral_energyband_middle_high
-------------------------

::

    curl http://www.freesound.org/api/sounds/<sound_id>/analysis/lowlevel/spectral_energyband_middle_high

**Essentia Algorithm**

http://essentia.upf.edu/documentation/reference/streaming_EnergyBand.html


**Stats**::


/min
/max
/dvar2
/dmean2
/dmean
/var
/dvar
/mean


**Distribution in Freesound**

    .. image:: _static/descriptors/lowlevel.spectral_energyband_middle_high.mean.png
        :height: 300px



lowlevel.barkbands_spread
-------------------------

::

    curl http://www.freesound.org/api/sounds/<sound_id>/analysis/lowlevel/barkbands_spread

**Essentia Algorithm**

http://essentia.upf.edu/documentation/reference/streaming_CentralMoments.html


**Stats**::


/min
/max
/dvar2
/dmean2
/dmean
/var
/dvar
/mean


**Distribution in Freesound**

    .. image:: _static/descriptors/lowlevel.barkbands_spread.mean.png
        :height: 300px



lowlevel.spectral_centroid
-------------------------

::

    curl http://www.freesound.org/api/sounds/<sound_id>/analysis/lowlevel/spectral_centroid

**Essentia Algorithm**

http://essentia.upf.edu/documentation/reference/streaming_Centroid.html


**Stats**::


/min
/max
/dvar2
/dmean2
/dmean
/var
/dvar
/mean


**Distribution in Freesound**

    .. image:: _static/descriptors/lowlevel.spectral_centroid.mean.png
        :height: 300px



lowlevel.pitch_salience
-------------------------

::

    curl http://www.freesound.org/api/sounds/<sound_id>/analysis/lowlevel/pitch_salience

**Essentia Algorithm**

http://essentia.upf.edu/documentation/reference/streaming_PitchSalience.html


**Stats**::


/min
/max
/dvar2
/dmean2
/dmean
/var
/dvar
/mean


**Distribution in Freesound**

    .. image:: _static/descriptors/lowlevel.pitch_salience.mean.png
        :height: 300px



lowlevel.silence_rate_60dB
-------------------------

::

    curl http://www.freesound.org/api/sounds/<sound_id>/analysis/lowlevel/silence_rate_60dB

**Essentia Algorithm**

http://essentia.upf.edu/documentation/reference/streaming_SilenceRate.html


**Stats**::


/min
/max
/dvar2
/dmean2
/dmean
/var
/dvar
/mean


**Distribution in Freesound**

    .. image:: _static/descriptors/lowlevel.silence_rate_60dB.mean.png
        :height: 300px



lowlevel.spectral_rolloff
-------------------------

::

    curl http://www.freesound.org/api/sounds/<sound_id>/analysis/lowlevel/spectral_rolloff

**Essentia Algorithm**

http://essentia.upf.edu/documentation/reference/streaming_RollOff.html


**Stats**::


/min
/max
/dvar2
/dmean2
/dmean
/var
/dvar
/mean


**Distribution in Freesound**

    .. image:: _static/descriptors/lowlevel.spectral_rolloff.mean.png
        :height: 300px



lowlevel.barkbands
-------------------------

::

    curl http://www.freesound.org/api/sounds/<sound_id>/analysis/lowlevel/barkbands

**Essentia Algorithm**

http://essentia.upf.edu/documentation/reference/streaming_BarkBands.html


**Stats**::


/min
/max
/dvar2
/dmean2
/dmean
/var
/dvar
/mean


**Distribution in Freesound**

    .. image:: _static/descriptors/lowlevel.barkbands.mean.000.png
        :height: 300px
    .. image:: _static/descriptors/lowlevel.barkbands.mean.001.png
        :height: 300px
    .. image:: _static/descriptors/lowlevel.barkbands.mean.002.png
        :height: 300px
    .. image:: _static/descriptors/lowlevel.barkbands.mean.003.png
        :height: 300px
    .. image:: _static/descriptors/lowlevel.barkbands.mean.004.png
        :height: 300px
    .. image:: _static/descriptors/lowlevel.barkbands.mean.005.png
        :height: 300px
    .. image:: _static/descriptors/lowlevel.barkbands.mean.006.png
        :height: 300px
    .. image:: _static/descriptors/lowlevel.barkbands.mean.007.png
        :height: 300px
    .. image:: _static/descriptors/lowlevel.barkbands.mean.008.png
        :height: 300px
    .. image:: _static/descriptors/lowlevel.barkbands.mean.009.png
        :height: 300px
    .. image:: _static/descriptors/lowlevel.barkbands.mean.010.png
        :height: 300px
    .. image:: _static/descriptors/lowlevel.barkbands.mean.011.png
        :height: 300px
    .. image:: _static/descriptors/lowlevel.barkbands.mean.012.png
        :height: 300px
    .. image:: _static/descriptors/lowlevel.barkbands.mean.013.png
        :height: 300px
    .. image:: _static/descriptors/lowlevel.barkbands.mean.014.png
        :height: 300px
    .. image:: _static/descriptors/lowlevel.barkbands.mean.015.png
        :height: 300px
    .. image:: _static/descriptors/lowlevel.barkbands.mean.016.png
        :height: 300px
    .. image:: _static/descriptors/lowlevel.barkbands.mean.017.png
        :height: 300px
    .. image:: _static/descriptors/lowlevel.barkbands.mean.018.png
        :height: 300px
    .. image:: _static/descriptors/lowlevel.barkbands.mean.019.png
        :height: 300px
    .. image:: _static/descriptors/lowlevel.barkbands.mean.020.png
        :height: 300px
    .. image:: _static/descriptors/lowlevel.barkbands.mean.021.png
        :height: 300px
    .. image:: _static/descriptors/lowlevel.barkbands.mean.022.png
        :height: 300px
    .. image:: _static/descriptors/lowlevel.barkbands.mean.023.png
        :height: 300px
    .. image:: _static/descriptors/lowlevel.barkbands.mean.024.png
        :height: 300px
    .. image:: _static/descriptors/lowlevel.barkbands.mean.025.png
        :height: 300px
    .. image:: _static/descriptors/lowlevel.barkbands.mean.026.png
        :height: 300px



lowlevel.spectral_energyband_low
-------------------------

::

    curl http://www.freesound.org/api/sounds/<sound_id>/analysis/lowlevel/spectral_energyband_low

**Essentia Algorithm**

http://essentia.upf.edu/documentation/reference/streaming_EnergyBand.html


**Stats**::


/min
/max
/dvar2
/dmean2
/dmean
/var
/dvar
/mean


**Distribution in Freesound**

    .. image:: _static/descriptors/lowlevel.spectral_energyband_low.mean.png
        :height: 300px



lowlevel.barkbands_skewness
-------------------------

::

    curl http://www.freesound.org/api/sounds/<sound_id>/analysis/lowlevel/barkbands_skewness

**Essentia Algorithm**

http://essentia.upf.edu/documentation/reference/streaming_CentralMoments.html


**Stats**::


/min
/max
/dvar2
/dmean2
/dmean
/var
/dvar
/mean


**Distribution in Freesound**

    .. image:: _static/descriptors/lowlevel.barkbands_skewness.mean.png
        :height: 300px



lowlevel.pitch_instantaneous_confidence
-------------------------

::

    curl http://www.freesound.org/api/sounds/<sound_id>/analysis/lowlevel/pitch_instantaneous_confidence

**Essentia Algorithm**

http://essentia.upf.edu/documentation/reference/streaming_PitchYinFFT.html


**Stats**::


/min
/max
/dvar2
/dmean2
/dmean
/var
/dvar
/mean


**Distribution in Freesound**

    .. image:: _static/descriptors/lowlevel.pitch_instantaneous_confidence.mean.png
        :height: 300px



lowlevel.spectral_energyband_middle_low
-------------------------

::

    curl http://www.freesound.org/api/sounds/<sound_id>/analysis/lowlevel/spectral_energyband_middle_low

**Essentia Algorithm**

http://essentia.upf.edu/documentation/reference/streaming_EnergyBand.html


**Stats**::


/min
/max
/dvar2
/dmean2
/dmean
/var
/dvar
/mean


**Distribution in Freesound**

    .. image:: _static/descriptors/lowlevel.spectral_energyband_middle_low.mean.png
        :height: 300px



lowlevel.spectral_strongpeak
-------------------------

::

    curl http://www.freesound.org/api/sounds/<sound_id>/analysis/lowlevel/spectral_strongpeak

**Essentia Algorithm**

http://essentia.upf.edu/documentation/reference/streaming_StrongPeak.html


**Stats**::


/min
/max
/dvar2
/dmean2
/dmean
/var
/dvar
/mean


**Distribution in Freesound**

    .. image:: _static/descriptors/lowlevel.spectral_strongpeak.mean.png
        :height: 300px



lowlevel.hfc
-------------------------

::

    curl http://www.freesound.org/api/sounds/<sound_id>/analysis/lowlevel/hfc

**Essentia Algorithm**

http://essentia.upf.edu/documentation/reference/streaming_HFC.html


**Stats**::


/min
/max
/dvar2
/dmean2
/dmean
/var
/dvar
/mean


**Distribution in Freesound**

    .. image:: _static/descriptors/lowlevel.hfc.mean.png
        :height: 300px



lowlevel.mfcc
-------------------------

::

    curl http://www.freesound.org/api/sounds/<sound_id>/analysis/lowlevel/mfcc

**Essentia Algorithm**

http://essentia.upf.edu/documentation/reference/streaming_MFCC.html


**Stats**::


/min
/max
/dvar2
/dmean2
/dmean
/var
/dvar
/mean


**Distribution in Freesound**

    .. image:: _static/descriptors/lowlevel.mfcc.mean.000.png
        :height: 300px
    .. image:: _static/descriptors/lowlevel.mfcc.mean.001.png
        :height: 300px
    .. image:: _static/descriptors/lowlevel.mfcc.mean.002.png
        :height: 300px
    .. image:: _static/descriptors/lowlevel.mfcc.mean.003.png
        :height: 300px
    .. image:: _static/descriptors/lowlevel.mfcc.mean.004.png
        :height: 300px
    .. image:: _static/descriptors/lowlevel.mfcc.mean.005.png
        :height: 300px
    .. image:: _static/descriptors/lowlevel.mfcc.mean.006.png
        :height: 300px
    .. image:: _static/descriptors/lowlevel.mfcc.mean.007.png
        :height: 300px
    .. image:: _static/descriptors/lowlevel.mfcc.mean.008.png
        :height: 300px
    .. image:: _static/descriptors/lowlevel.mfcc.mean.009.png
        :height: 300px
    .. image:: _static/descriptors/lowlevel.mfcc.mean.010.png
        :height: 300px
    .. image:: _static/descriptors/lowlevel.mfcc.mean.011.png
        :height: 300px
    .. image:: _static/descriptors/lowlevel.mfcc.mean.012.png
        :height: 300px



lowlevel.spectral_energy
-------------------------

::

    curl http://www.freesound.org/api/sounds/<sound_id>/analysis/lowlevel/spectral_energy

**Essentia Algorithm**

http://essentia.upf.edu/documentation/reference/streaming_Energy.html


**Stats**::


/min
/max
/dvar2
/dmean2
/dmean
/var
/dvar
/mean


**Distribution in Freesound**

    .. image:: _static/descriptors/lowlevel.spectral_energy.mean.png
        :height: 300px



lowlevel.spectral_flatness_db
-------------------------

::

    curl http://www.freesound.org/api/sounds/<sound_id>/analysis/lowlevel/spectral_flatness_db

**Essentia Algorithm**

http://essentia.upf.edu/documentation/reference/streaming_FlatnessDB.html


**Stats**::


/min
/max
/dvar2
/dmean2
/dmean
/var
/dvar
/mean


**Distribution in Freesound**

    .. image:: _static/descriptors/lowlevel.spectral_flatness_db.mean.png
        :height: 300px



lowlevel.frequency_bands
-------------------------

::

    curl http://www.freesound.org/api/sounds/<sound_id>/analysis/lowlevel/frequency_bands

**Essentia Algorithm**

http://essentia.upf.edu/documentation/reference/streaming_FrequencyBands.html


**Stats**::


/min
/max
/dvar2
/dmean2
/dmean
/var
/dvar
/mean


**Distribution in Freesound**

    .. image:: _static/descriptors/lowlevel.frequency_bands.mean.000.png
        :height: 300px
    .. image:: _static/descriptors/lowlevel.frequency_bands.mean.001.png
        :height: 300px
    .. image:: _static/descriptors/lowlevel.frequency_bands.mean.002.png
        :height: 300px
    .. image:: _static/descriptors/lowlevel.frequency_bands.mean.003.png
        :height: 300px
    .. image:: _static/descriptors/lowlevel.frequency_bands.mean.004.png
        :height: 300px
    .. image:: _static/descriptors/lowlevel.frequency_bands.mean.005.png
        :height: 300px
    .. image:: _static/descriptors/lowlevel.frequency_bands.mean.006.png
        :height: 300px
    .. image:: _static/descriptors/lowlevel.frequency_bands.mean.007.png
        :height: 300px
    .. image:: _static/descriptors/lowlevel.frequency_bands.mean.008.png
        :height: 300px
    .. image:: _static/descriptors/lowlevel.frequency_bands.mean.009.png
        :height: 300px
    .. image:: _static/descriptors/lowlevel.frequency_bands.mean.010.png
        :height: 300px
    .. image:: _static/descriptors/lowlevel.frequency_bands.mean.011.png
        :height: 300px
    .. image:: _static/descriptors/lowlevel.frequency_bands.mean.012.png
        :height: 300px
    .. image:: _static/descriptors/lowlevel.frequency_bands.mean.013.png
        :height: 300px
    .. image:: _static/descriptors/lowlevel.frequency_bands.mean.014.png
        :height: 300px
    .. image:: _static/descriptors/lowlevel.frequency_bands.mean.015.png
        :height: 300px
    .. image:: _static/descriptors/lowlevel.frequency_bands.mean.016.png
        :height: 300px
    .. image:: _static/descriptors/lowlevel.frequency_bands.mean.017.png
        :height: 300px
    .. image:: _static/descriptors/lowlevel.frequency_bands.mean.018.png
        :height: 300px
    .. image:: _static/descriptors/lowlevel.frequency_bands.mean.019.png
        :height: 300px
    .. image:: _static/descriptors/lowlevel.frequency_bands.mean.020.png
        :height: 300px
    .. image:: _static/descriptors/lowlevel.frequency_bands.mean.021.png
        :height: 300px
    .. image:: _static/descriptors/lowlevel.frequency_bands.mean.022.png
        :height: 300px
    .. image:: _static/descriptors/lowlevel.frequency_bands.mean.023.png
        :height: 300px
    .. image:: _static/descriptors/lowlevel.frequency_bands.mean.024.png
        :height: 300px
    .. image:: _static/descriptors/lowlevel.frequency_bands.mean.025.png
        :height: 300px
    .. image:: _static/descriptors/lowlevel.frequency_bands.mean.026.png
        :height: 300px
    .. image:: _static/descriptors/lowlevel.frequency_bands.mean.027.png
        :height: 300px



lowlevel.zerocrossingrate
-------------------------

::

    curl http://www.freesound.org/api/sounds/<sound_id>/analysis/lowlevel/zerocrossingrate

**Essentia Algorithm**

http://essentia.upf.edu/documentation/reference/streaming_ZeroCrossingRate.html


**Stats**::


/min
/max
/dvar2
/dmean2
/dmean
/var
/dvar
/mean


**Distribution in Freesound**

    .. image:: _static/descriptors/lowlevel.zerocrossingrate.mean.png
        :height: 300px



lowlevel.spectral_decrease
-------------------------

::

    curl http://www.freesound.org/api/sounds/<sound_id>/analysis/lowlevel/spectral_decrease

**Essentia Algorithm**

http://essentia.upf.edu/documentation/reference/streaming_Decrease.html


**Stats**::


/min
/max
/dvar2
/dmean2
/dmean
/var
/dvar
/mean


**Distribution in Freesound**

    .. image:: _static/descriptors/lowlevel.spectral_decrease.mean.png
        :height: 300px



lowlevel.spectral_crest
-------------------------

::

    curl http://www.freesound.org/api/sounds/<sound_id>/analysis/lowlevel/spectral_crest

**Essentia Algorithm**

http://essentia.upf.edu/documentation/reference/streaming_Crest.html


**Stats**::


/min
/max
/dvar2
/dmean2
/dmean
/var
/dvar
/mean


**Distribution in Freesound**

    .. image:: _static/descriptors/lowlevel.spectral_crest.mean.png
        :height: 300px



Rhythm Descriptors
>>>>>>>>>>>>>>>>>>>>


rhythm.first_peak_bpm
-------------------------

::

    curl http://www.freesound.org/api/sounds/<sound_id>/analysis/rhythm/first_peak_bpm

**Essentia Algorithm**

http://essentia.upf.edu/documentation/reference/streaming_BpmHistogramDescriptors.html



rhythm.onset_times
-------------------------

::

    curl http://www.freesound.org/api/sounds/<sound_id>/analysis/rhythm/onset_times

**Essentia Algorithm**

http://essentia.upf.edu/documentation/reference/streaming_OnsetRate.html



rhythm.beats_loudness
-------------------------

::

    curl http://www.freesound.org/api/sounds/<sound_id>/analysis/rhythm/beats_loudness

**Essentia Algorithm**

http://essentia.upf.edu/documentation/reference/streaming_BeatsLoudness.html


**Stats**::


/min
/max
/dvar2
/dmean2
/dmean
/var
/dvar
/mean


**Distribution in Freesound**

    .. image:: _static/descriptors/rhythm.beats_loudness.mean.png
        :height: 300px



rhythm.first_peak_spread
-------------------------

::

    curl http://www.freesound.org/api/sounds/<sound_id>/analysis/rhythm/first_peak_spread

**Essentia Algorithm**

http://essentia.upf.edu/documentation/reference/streaming_BpmHistogramDescriptors.html



rhythm.second_peak_weight
-------------------------

::

    curl http://www.freesound.org/api/sounds/<sound_id>/analysis/rhythm/second_peak_weight

**Essentia Algorithm**

http://essentia.upf.edu/documentation/reference/streaming_BpmHistogramDescriptors.html



rhythm.bpm
-------------------------

::

    curl http://www.freesound.org/api/sounds/<sound_id>/analysis/rhythm/bpm

**Essentia Algorithm**

http://essentia.upf.edu/documentation/reference/streaming_RhythmExtractor2013.html



rhythm.bpm_intervals
-------------------------

::

    curl http://www.freesound.org/api/sounds/<sound_id>/analysis/rhythm/bpm_intervals

**Essentia Algorithm**

http://essentia.upf.edu/documentation/reference/streaming_RhythmExtractor2013.html



rhythm.first_peak_weight
-------------------------

::

    curl http://www.freesound.org/api/sounds/<sound_id>/analysis/rhythm/first_peak_weight

**Essentia Algorithm**

http://essentia.upf.edu/documentation/reference/streaming_BpmHistogramDescriptors.html



rhythm.bpm_estimates
-------------------------

::

    curl http://www.freesound.org/api/sounds/<sound_id>/analysis/rhythm/bpm_estimates

**Essentia Algorithm**

http://essentia.upf.edu/documentation/reference/streaming_RhythmExtractor2013.html



rhythm.beats_loudness_band_ratio
-------------------------

::

    curl http://www.freesound.org/api/sounds/<sound_id>/analysis/rhythm/beats_loudness_band_ratio

**Essentia Algorithm**

http://essentia.upf.edu/documentation/reference/streaming_BeatsLoudness.html


**Stats**::


/min
/max
/dvar2
/dmean2
/dmean
/var
/dvar
/mean


**Distribution in Freesound**

    .. image:: _static/descriptors/rhythm.beats_loudness_band_ratio.mean.000.png
        :height: 300px
    .. image:: _static/descriptors/rhythm.beats_loudness_band_ratio.mean.001.png
        :height: 300px
    .. image:: _static/descriptors/rhythm.beats_loudness_band_ratio.mean.002.png
        :height: 300px
    .. image:: _static/descriptors/rhythm.beats_loudness_band_ratio.mean.003.png
        :height: 300px
    .. image:: _static/descriptors/rhythm.beats_loudness_band_ratio.mean.004.png
        :height: 300px
    .. image:: _static/descriptors/rhythm.beats_loudness_band_ratio.mean.005.png
        :height: 300px



rhythm.second_peak_bpm
-------------------------

::

    curl http://www.freesound.org/api/sounds/<sound_id>/analysis/rhythm/second_peak_bpm

**Essentia Algorithm**

http://essentia.upf.edu/documentation/reference/streaming_BpmHistogramDescriptors.html



rhythm.onset_rate
-------------------------

::

    curl http://www.freesound.org/api/sounds/<sound_id>/analysis/rhythm/onset_rate

**Essentia Algorithm**

http://essentia.upf.edu/documentation/reference/streaming_OnsetRate.html



rhythm.beats_position
-------------------------

::

    curl http://www.freesound.org/api/sounds/<sound_id>/analysis/rhythm/beats_position

**Essentia Algorithm**

http://essentia.upf.edu/documentation/reference/streaming_RhythmExtractor2013.html



rhythm.second_peak_spread
-------------------------

::

    curl http://www.freesound.org/api/sounds/<sound_id>/analysis/rhythm/second_peak_spread

**Essentia Algorithm**

http://essentia.upf.edu/documentation/reference/streaming_BpmHistogramDescriptors.html



Tonal Descriptors
>>>>>>>>>>>>>>>>>>>>


tonal.hpcp
-------------------------

::

    curl http://www.freesound.org/api/sounds/<sound_id>/analysis/tonal/hpcp

**Essentia Algorithm**

http://essentia.upf.edu/documentation/reference/streaming_HPCP.html


**Stats**::


/min
/max
/dvar2
/dmean2
/dmean
/var
/dvar
/mean


**Distribution in Freesound**

    .. image:: _static/descriptors/tonal.hpcp.mean.000.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp.mean.001.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp.mean.002.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp.mean.003.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp.mean.004.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp.mean.005.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp.mean.006.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp.mean.007.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp.mean.008.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp.mean.009.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp.mean.010.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp.mean.011.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp.mean.012.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp.mean.013.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp.mean.014.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp.mean.015.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp.mean.016.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp.mean.017.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp.mean.018.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp.mean.019.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp.mean.020.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp.mean.021.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp.mean.022.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp.mean.023.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp.mean.024.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp.mean.025.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp.mean.026.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp.mean.027.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp.mean.028.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp.mean.029.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp.mean.030.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp.mean.031.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp.mean.032.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp.mean.033.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp.mean.034.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp.mean.035.png
        :height: 300px



tonal.chords_number_rate
-------------------------

::

    curl http://www.freesound.org/api/sounds/<sound_id>/analysis/tonal/chords_number_rate

**Essentia Algorithm**

http://essentia.upf.edu/documentation/reference/streaming_ChordsDescriptors.html



tonal.key_strength
-------------------------

::

    curl http://www.freesound.org/api/sounds/<sound_id>/analysis/tonal/key_strength

**Essentia Algorithm**

http://essentia.upf.edu/documentation/reference/streaming_Key.html



tonal.chords_progression
-------------------------

::

    curl http://www.freesound.org/api/sounds/<sound_id>/analysis/tonal/chords_progression

**Essentia Algorithm**

http://essentia.upf.edu/documentation/reference/streaming_ChordsDetection.html



tonal.key_scale
-------------------------

::

    curl http://www.freesound.org/api/sounds/<sound_id>/analysis/tonal/key_scale

**Essentia Algorithm**

http://essentia.upf.edu/documentation/reference/streaming_Key.html



tonal.chords_strength
-------------------------

::

    curl http://www.freesound.org/api/sounds/<sound_id>/analysis/tonal/chords_strength

**Essentia Algorithm**

http://essentia.upf.edu/documentation/reference/streaming_ChordsDetection.html


**Stats**::


/min
/max
/dvar2
/dmean2
/dmean
/var
/dvar
/mean


**Distribution in Freesound**

    .. image:: _static/descriptors/tonal.chords_strength.mean.png
        :height: 300px



tonal.key_key
-------------------------

::

    curl http://www.freesound.org/api/sounds/<sound_id>/analysis/tonal/key_key

**Essentia Algorithm**

http://essentia.upf.edu/documentation/reference/streaming_Key.html



tonal.chords_changes_rate
-------------------------

::

    curl http://www.freesound.org/api/sounds/<sound_id>/analysis/tonal/chords_changes_rate

**Essentia Algorithm**

http://essentia.upf.edu/documentation/reference/streaming_ChordsDescriptors.html



tonal.chords_scale
-------------------------

::

    curl http://www.freesound.org/api/sounds/<sound_id>/analysis/tonal/chords_scale

**Essentia Algorithm**

http://essentia.upf.edu/documentation/reference/streaming_ChordsDescriptors.html



tonal.chords_histogram
-------------------------

::

    curl http://www.freesound.org/api/sounds/<sound_id>/analysis/tonal/chords_histogram

**Essentia Algorithm**

http://essentia.upf.edu/documentation/reference/streaming_ChordsDescriptors.html



tonal.chords_key
-------------------------

::

    curl http://www.freesound.org/api/sounds/<sound_id>/analysis/tonal/chords_key

**Essentia Algorithm**

http://essentia.upf.edu/documentation/reference/streaming_ChordsDescriptors.html



tonal.tuning_frequency
-------------------------

::

    curl http://www.freesound.org/api/sounds/<sound_id>/analysis/tonal/tuning_frequency

**Essentia Algorithm**

http://essentia.upf.edu/documentation/reference/streaming_TuningFrequency.html


**Stats**::


/min
/max
/dvar2
/dmean2
/dmean
/var
/dvar
/mean


**Distribution in Freesound**

    .. image:: _static/descriptors/tonal.tuning_frequency.mean.png
        :height: 300px



tonal.hpcp_highres
-------------------------

::

    curl http://www.freesound.org/api/sounds/<sound_id>/analysis/tonal/hpcp_highres

**Essentia Algorithm**

http://essentia.upf.edu/documentation/reference/streaming_HPCP.html


**Stats**::


/min
/max
/dvar2
/dmean2
/dmean
/var
/dvar
/mean


**Distribution in Freesound**

    .. image:: _static/descriptors/tonal.hpcp_highres.mean.000.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp_highres.mean.001.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp_highres.mean.002.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp_highres.mean.003.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp_highres.mean.004.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp_highres.mean.005.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp_highres.mean.006.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp_highres.mean.007.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp_highres.mean.008.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp_highres.mean.009.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp_highres.mean.010.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp_highres.mean.011.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp_highres.mean.012.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp_highres.mean.013.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp_highres.mean.014.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp_highres.mean.015.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp_highres.mean.016.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp_highres.mean.017.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp_highres.mean.018.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp_highres.mean.019.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp_highres.mean.020.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp_highres.mean.021.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp_highres.mean.022.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp_highres.mean.023.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp_highres.mean.024.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp_highres.mean.025.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp_highres.mean.026.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp_highres.mean.027.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp_highres.mean.028.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp_highres.mean.029.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp_highres.mean.030.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp_highres.mean.031.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp_highres.mean.032.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp_highres.mean.033.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp_highres.mean.034.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp_highres.mean.035.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp_highres.mean.036.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp_highres.mean.037.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp_highres.mean.038.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp_highres.mean.039.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp_highres.mean.040.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp_highres.mean.041.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp_highres.mean.042.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp_highres.mean.043.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp_highres.mean.044.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp_highres.mean.045.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp_highres.mean.046.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp_highres.mean.047.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp_highres.mean.048.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp_highres.mean.049.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp_highres.mean.050.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp_highres.mean.051.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp_highres.mean.052.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp_highres.mean.053.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp_highres.mean.054.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp_highres.mean.055.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp_highres.mean.056.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp_highres.mean.057.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp_highres.mean.058.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp_highres.mean.059.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp_highres.mean.060.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp_highres.mean.061.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp_highres.mean.062.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp_highres.mean.063.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp_highres.mean.064.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp_highres.mean.065.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp_highres.mean.066.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp_highres.mean.067.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp_highres.mean.068.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp_highres.mean.069.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp_highres.mean.070.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp_highres.mean.071.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp_highres.mean.072.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp_highres.mean.073.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp_highres.mean.074.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp_highres.mean.075.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp_highres.mean.076.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp_highres.mean.077.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp_highres.mean.078.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp_highres.mean.079.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp_highres.mean.080.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp_highres.mean.081.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp_highres.mean.082.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp_highres.mean.083.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp_highres.mean.084.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp_highres.mean.085.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp_highres.mean.086.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp_highres.mean.087.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp_highres.mean.088.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp_highres.mean.089.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp_highres.mean.090.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp_highres.mean.091.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp_highres.mean.092.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp_highres.mean.093.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp_highres.mean.094.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp_highres.mean.095.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp_highres.mean.096.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp_highres.mean.097.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp_highres.mean.098.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp_highres.mean.099.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp_highres.mean.100.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp_highres.mean.101.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp_highres.mean.102.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp_highres.mean.103.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp_highres.mean.104.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp_highres.mean.105.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp_highres.mean.106.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp_highres.mean.107.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp_highres.mean.108.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp_highres.mean.109.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp_highres.mean.110.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp_highres.mean.111.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp_highres.mean.112.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp_highres.mean.113.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp_highres.mean.114.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp_highres.mean.115.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp_highres.mean.116.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp_highres.mean.117.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp_highres.mean.118.png
        :height: 300px
    .. image:: _static/descriptors/tonal.hpcp_highres.mean.119.png
        :height: 300px



