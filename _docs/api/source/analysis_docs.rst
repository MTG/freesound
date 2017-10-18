
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


metadata.version
-------------------------

::

    curl https://freesound.org/api/sounds/<sound_id>/analysis/metadata/version


Lowlevel Descriptors
>>>>>>>>>>>>>>>>>>>>


lowlevel.spectral_complexity
-------------------------

::

    curl https://freesound.org/api/sounds/<sound_id>/analysis/lowlevel/spectral_complexity

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

    curl https://freesound.org/api/sounds/<sound_id>/analysis/lowlevel/silence_rate_20dB

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

    .. image:: _static/descriptors/lowlevel.silence_rate_20dB.mean.png
        :height: 300px



lowlevel.erb_bands
-------------------------

::

    curl https://freesound.org/api/sounds/<sound_id>/analysis/lowlevel/erb_bands

**Essentia Algorithm**

http://essentia.upf.edu/documentation/reference/streaming_ERBBands.html


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

    .. image:: _static/descriptors/lowlevel.erb_bands.mean.000.png
        :height: 300px
    .. image:: _static/descriptors/lowlevel.erb_bands.mean.001.png
        :height: 300px
    .. image:: _static/descriptors/lowlevel.erb_bands.mean.002.png
        :height: 300px
    .. image:: _static/descriptors/lowlevel.erb_bands.mean.003.png
        :height: 300px
    .. image:: _static/descriptors/lowlevel.erb_bands.mean.004.png
        :height: 300px
    .. image:: _static/descriptors/lowlevel.erb_bands.mean.005.png
        :height: 300px
    .. image:: _static/descriptors/lowlevel.erb_bands.mean.006.png
        :height: 300px
    .. image:: _static/descriptors/lowlevel.erb_bands.mean.007.png
        :height: 300px
    .. image:: _static/descriptors/lowlevel.erb_bands.mean.008.png
        :height: 300px
    .. image:: _static/descriptors/lowlevel.erb_bands.mean.009.png
        :height: 300px
    .. image:: _static/descriptors/lowlevel.erb_bands.mean.010.png
        :height: 300px
    .. image:: _static/descriptors/lowlevel.erb_bands.mean.011.png
        :height: 300px
    .. image:: _static/descriptors/lowlevel.erb_bands.mean.012.png
        :height: 300px
    .. image:: _static/descriptors/lowlevel.erb_bands.mean.013.png
        :height: 300px
    .. image:: _static/descriptors/lowlevel.erb_bands.mean.014.png
        :height: 300px
    .. image:: _static/descriptors/lowlevel.erb_bands.mean.015.png
        :height: 300px
    .. image:: _static/descriptors/lowlevel.erb_bands.mean.016.png
        :height: 300px
    .. image:: _static/descriptors/lowlevel.erb_bands.mean.017.png
        :height: 300px



lowlevel.average_loudness
-------------------------

::

    curl https://freesound.org/api/sounds/<sound_id>/analysis/lowlevel/average_loudness

**Essentia Algorithm**

http://essentia.upf.edu/documentation/reference/streaming_Loudness.html
    .. image:: _static/descriptors/lowlevel.average_loudness.png
        :height: 300px



lowlevel.spectral_rms
-------------------------

::

    curl https://freesound.org/api/sounds/<sound_id>/analysis/lowlevel/spectral_rms

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



lowlevel.spectral_kurtosis
-------------------------

::

    curl https://freesound.org/api/sounds/<sound_id>/analysis/lowlevel/spectral_kurtosis

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

    curl https://freesound.org/api/sounds/<sound_id>/analysis/lowlevel/barkbands_kurtosis

**Essentia Algorithm**

http://essentia.upf.edu/documentation/reference/streaming_CentralMoments.html


**Stats**::


/min
/max
/dmean2
/dmean
/var
/mean


**Distribution in Freesound**

    .. image:: _static/descriptors/lowlevel.barkbands_kurtosis.mean.png
        :height: 300px



lowlevel.scvalleys
-------------------------

::

    curl https://freesound.org/api/sounds/<sound_id>/analysis/lowlevel/scvalleys

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

    curl https://freesound.org/api/sounds/<sound_id>/analysis/lowlevel/spectral_spread

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

    .. image:: _static/descriptors/lowlevel.spectral_spread.mean.png
        :height: 300px



lowlevel.pitch
-------------------------

::

    curl https://freesound.org/api/sounds/<sound_id>/analysis/lowlevel/pitch

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



lowlevel.dissonance
-------------------------

::

    curl https://freesound.org/api/sounds/<sound_id>/analysis/lowlevel/dissonance

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

    curl https://freesound.org/api/sounds/<sound_id>/analysis/lowlevel/spectral_energyband_high

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



lowlevel.gfcc
-------------------------

::

    curl https://freesound.org/api/sounds/<sound_id>/analysis/lowlevel/gfcc

**Essentia Algorithm**

http://essentia.upf.edu/documentation/reference/streaming_GFCC.html


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

    .. image:: _static/descriptors/lowlevel.gfcc.mean.000.png
        :height: 300px
    .. image:: _static/descriptors/lowlevel.gfcc.mean.001.png
        :height: 300px
    .. image:: _static/descriptors/lowlevel.gfcc.mean.002.png
        :height: 300px
    .. image:: _static/descriptors/lowlevel.gfcc.mean.003.png
        :height: 300px
    .. image:: _static/descriptors/lowlevel.gfcc.mean.004.png
        :height: 300px
    .. image:: _static/descriptors/lowlevel.gfcc.mean.005.png
        :height: 300px
    .. image:: _static/descriptors/lowlevel.gfcc.mean.006.png
        :height: 300px
    .. image:: _static/descriptors/lowlevel.gfcc.mean.007.png
        :height: 300px
    .. image:: _static/descriptors/lowlevel.gfcc.mean.008.png
        :height: 300px
    .. image:: _static/descriptors/lowlevel.gfcc.mean.009.png
        :height: 300px
    .. image:: _static/descriptors/lowlevel.gfcc.mean.010.png
        :height: 300px
    .. image:: _static/descriptors/lowlevel.gfcc.mean.011.png
        :height: 300px
    .. image:: _static/descriptors/lowlevel.gfcc.mean.012.png
        :height: 300px



lowlevel.spectral_flux
-------------------------

::

    curl https://freesound.org/api/sounds/<sound_id>/analysis/lowlevel/spectral_flux

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

    curl https://freesound.org/api/sounds/<sound_id>/analysis/lowlevel/silence_rate_30dB

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

    .. image:: _static/descriptors/lowlevel.silence_rate_30dB.mean.png
        :height: 300px



lowlevel.spectral_contrast
-------------------------

::

    curl https://freesound.org/api/sounds/<sound_id>/analysis/lowlevel/spectral_contrast

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

    curl https://freesound.org/api/sounds/<sound_id>/analysis/lowlevel/spectral_energyband_middle_high

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

    curl https://freesound.org/api/sounds/<sound_id>/analysis/lowlevel/barkbands_spread

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

    curl https://freesound.org/api/sounds/<sound_id>/analysis/lowlevel/spectral_centroid

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

    curl https://freesound.org/api/sounds/<sound_id>/analysis/lowlevel/pitch_salience

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

    curl https://freesound.org/api/sounds/<sound_id>/analysis/lowlevel/silence_rate_60dB

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



lowlevel.spectral_entropy
-------------------------

::

    curl https://freesound.org/api/sounds/<sound_id>/analysis/lowlevel/spectral_entropy

**Essentia Algorithm**

http://essentia.upf.edu/documentation/reference/streaming_Entropy.html


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

    .. image:: _static/descriptors/lowlevel.spectral_entropy.mean.png
        :height: 300px



lowlevel.spectral_rolloff
-------------------------

::

    curl https://freesound.org/api/sounds/<sound_id>/analysis/lowlevel/spectral_rolloff

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

    curl https://freesound.org/api/sounds/<sound_id>/analysis/lowlevel/barkbands

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

    curl https://freesound.org/api/sounds/<sound_id>/analysis/lowlevel/spectral_energyband_low

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

    curl https://freesound.org/api/sounds/<sound_id>/analysis/lowlevel/barkbands_skewness

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

    curl https://freesound.org/api/sounds/<sound_id>/analysis/lowlevel/pitch_instantaneous_confidence

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

    curl https://freesound.org/api/sounds/<sound_id>/analysis/lowlevel/spectral_energyband_middle_low

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

    curl https://freesound.org/api/sounds/<sound_id>/analysis/lowlevel/spectral_strongpeak

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



lowlevel.startFrame
-------------------------

::

    curl https://freesound.org/api/sounds/<sound_id>/analysis/lowlevel/startFrame

**Essentia Algorithm**

http://essentia.upf.edu/documentation/reference/streaming_StartStopSilence.html
    .. image:: _static/descriptors/lowlevel.startFrame.png
        :height: 300px



lowlevel.spectral_decrease
-------------------------

::

    curl https://freesound.org/api/sounds/<sound_id>/analysis/lowlevel/spectral_decrease

**Essentia Algorithm**

http://essentia.upf.edu/documentation/reference/streaming_Decrease.html


**Stats**::


/dmean2
/dmean
/mean
/max
/min


**Distribution in Freesound**

    .. image:: _static/descriptors/lowlevel.spectral_decrease.mean.png
        :height: 300px



lowlevel.stopFrame
-------------------------

::

    curl https://freesound.org/api/sounds/<sound_id>/analysis/lowlevel/stopFrame

**Essentia Algorithm**

http://essentia.upf.edu/documentation/reference/streaming_StartStopSilence.html
    .. image:: _static/descriptors/lowlevel.stopFrame.png
        :height: 300px



lowlevel.mfcc
-------------------------

::

    curl https://freesound.org/api/sounds/<sound_id>/analysis/lowlevel/mfcc

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

    curl https://freesound.org/api/sounds/<sound_id>/analysis/lowlevel/spectral_energy

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

    curl https://freesound.org/api/sounds/<sound_id>/analysis/lowlevel/spectral_flatness_db

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

    curl https://freesound.org/api/sounds/<sound_id>/analysis/lowlevel/frequency_bands

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

    curl https://freesound.org/api/sounds/<sound_id>/analysis/lowlevel/zerocrossingrate

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



lowlevel.spectral_skewness
-------------------------

::

    curl https://freesound.org/api/sounds/<sound_id>/analysis/lowlevel/spectral_skewness

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



lowlevel.hfc
-------------------------

::

    curl https://freesound.org/api/sounds/<sound_id>/analysis/lowlevel/hfc

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



lowlevel.spectral_crest
-------------------------

::

    curl https://freesound.org/api/sounds/<sound_id>/analysis/lowlevel/spectral_crest

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

    curl https://freesound.org/api/sounds/<sound_id>/analysis/rhythm/first_peak_bpm

**Essentia Algorithm**

http://essentia.upf.edu/documentation/reference/streaming_BpmHistogramDescriptors.html


**Stats**::


/max
/min
/mean


**Distribution in Freesound**

    .. image:: _static/descriptors/rhythm.first_peak_bpm.mean.png
        :height: 300px



rhythm.onset_times
-------------------------

::

    curl https://freesound.org/api/sounds/<sound_id>/analysis/rhythm/onset_times

**Essentia Algorithm**

http://essentia.upf.edu/documentation/reference/streaming_OnsetRate.html



rhythm.beats_count
-------------------------

::

    curl https://freesound.org/api/sounds/<sound_id>/analysis/rhythm/beats_count

**Essentia Algorithm**

http://essentia.upf.edu/documentation/reference/streaming_RhythmExtractor2013.html
    .. image:: _static/descriptors/rhythm.beats_count.png
        :height: 300px



rhythm.beats_loudness
-------------------------

::

    curl https://freesound.org/api/sounds/<sound_id>/analysis/rhythm/beats_loudness

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

    curl https://freesound.org/api/sounds/<sound_id>/analysis/rhythm/first_peak_spread

**Essentia Algorithm**

http://essentia.upf.edu/documentation/reference/streaming_BpmHistogramDescriptors.html


**Stats**::


/max
/min
/mean


**Distribution in Freesound**

    .. image:: _static/descriptors/rhythm.first_peak_spread.mean.png
        :height: 300px



rhythm.second_peak_weight
-------------------------

::

    curl https://freesound.org/api/sounds/<sound_id>/analysis/rhythm/second_peak_weight

**Essentia Algorithm**

http://essentia.upf.edu/documentation/reference/streaming_BpmHistogramDescriptors.html


**Stats**::


/max
/min
/mean


**Distribution in Freesound**

    .. image:: _static/descriptors/rhythm.second_peak_weight.mean.png
        :height: 300px



rhythm.bpm
-------------------------

::

    curl https://freesound.org/api/sounds/<sound_id>/analysis/rhythm/bpm

**Essentia Algorithm**

http://essentia.upf.edu/documentation/reference/streaming_RhythmExtractor2013.html
    .. image:: _static/descriptors/rhythm.bpm.png
        :height: 300px



rhythm.bpm_intervals
-------------------------

::

    curl https://freesound.org/api/sounds/<sound_id>/analysis/rhythm/bpm_intervals

**Essentia Algorithm**

http://essentia.upf.edu/documentation/reference/streaming_RhythmExtractor2013.html



rhythm.onset_count
-------------------------

::

    curl https://freesound.org/api/sounds/<sound_id>/analysis/rhythm/onset_count

**Essentia Algorithm**

http://essentia.upf.edu/documentation/reference/streaming_OnsetRate.html
    .. image:: _static/descriptors/rhythm.onset_count.png
        :height: 300px



rhythm.second_peak_spread
-------------------------

::

    curl https://freesound.org/api/sounds/<sound_id>/analysis/rhythm/second_peak_spread

**Essentia Algorithm**

http://essentia.upf.edu/documentation/reference/streaming_BpmHistogramDescriptors.html


**Stats**::


/max
/min
/mean


**Distribution in Freesound**

    .. image:: _static/descriptors/rhythm.second_peak_spread.mean.png
        :height: 300px



rhythm.beats_loudness_band_ratio
-------------------------

::

    curl https://freesound.org/api/sounds/<sound_id>/analysis/rhythm/beats_loudness_band_ratio

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

    curl https://freesound.org/api/sounds/<sound_id>/analysis/rhythm/second_peak_bpm

**Essentia Algorithm**

http://essentia.upf.edu/documentation/reference/streaming_BpmHistogramDescriptors.html


**Stats**::


/max
/min
/mean


**Distribution in Freesound**

    .. image:: _static/descriptors/rhythm.second_peak_bpm.mean.png
        :height: 300px



rhythm.onset_rate
-------------------------

::

    curl https://freesound.org/api/sounds/<sound_id>/analysis/rhythm/onset_rate

**Essentia Algorithm**

http://essentia.upf.edu/documentation/reference/streaming_OnsetDetection.html


rhythm.beats_position
-------------------------

::

    curl https://freesound.org/api/sounds/<sound_id>/analysis/rhythm/beats_position

**Essentia Algorithm**

http://essentia.upf.edu/documentation/reference/streaming_RhythmExtractor2013.html



rhythm.first_peak_weight
-------------------------

::

    curl https://freesound.org/api/sounds/<sound_id>/analysis/rhythm/first_peak_weight

**Essentia Algorithm**

http://essentia.upf.edu/documentation/reference/streaming_BpmHistogramDescriptors.html


**Stats**::


/max
/min
/mean


**Distribution in Freesound**

    .. image:: _static/descriptors/rhythm.first_peak_weight.mean.png
        :height: 300px



Tonal Descriptors
>>>>>>>>>>>>>>>>>>>>


tonal.hpcp_entropy
-------------------------

::

    curl https://freesound.org/api/sounds/<sound_id>/analysis/tonal/hpcp_entropy

**Essentia Algorithm**

http://essentia.upf.edu/documentation/reference/streaming_Entropy.html


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

    .. image:: _static/descriptors/tonal.hpcp_entropy.mean.png
        :height: 300px



tonal.chords_scale
-------------------------

::

    curl https://freesound.org/api/sounds/<sound_id>/analysis/tonal/chords_scale

**Essentia Algorithm**

http://essentia.upf.edu/documentation/reference/streaming_ChordsDescriptors.html



tonal.chords_number_rate
-------------------------

::

    curl https://freesound.org/api/sounds/<sound_id>/analysis/tonal/chords_number_rate

**Essentia Algorithm**

http://essentia.upf.edu/documentation/reference/streaming_ChordsDescriptors.html
    .. image:: _static/descriptors/tonal.chords_number_rate.png
        :height: 300px



tonal.key_strength
-------------------------

::

    curl https://freesound.org/api/sounds/<sound_id>/analysis/tonal/key_strength

**Essentia Algorithm**

http://essentia.upf.edu/documentation/reference/streaming_Key.html
    .. image:: _static/descriptors/tonal.key_strength.png
        :height: 300px



tonal.chords_progression
-------------------------

::

    curl https://freesound.org/api/sounds/<sound_id>/analysis/tonal/chords_progression

**Essentia Algorithm**

http://essentia.upf.edu/documentation/reference/streaming_ChordsDetection.html



tonal.key_scale
-------------------------

::

    curl https://freesound.org/api/sounds/<sound_id>/analysis/tonal/key_scale

**Essentia Algorithm**

http://essentia.upf.edu/documentation/reference/streaming_Key.html



tonal.chords_strength
-------------------------

::

    curl https://freesound.org/api/sounds/<sound_id>/analysis/tonal/chords_strength

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

    curl https://freesound.org/api/sounds/<sound_id>/analysis/tonal/key_key

**Essentia Algorithm**

http://essentia.upf.edu/documentation/reference/streaming_Key.html



tonal.chords_changes_rate
-------------------------

::

    curl https://freesound.org/api/sounds/<sound_id>/analysis/tonal/chords_changes_rate

**Essentia Algorithm**

http://essentia.upf.edu/documentation/reference/streaming_ChordsDescriptors.html
    .. image:: _static/descriptors/tonal.chords_changes_rate.png
        :height: 300px



tonal.chords_count
-------------------------

::

    curl https://freesound.org/api/sounds/<sound_id>/analysis/tonal/chords_count

**Essentia Algorithm**

http://essentia.upf.edu/documentation/reference/streaming_ChordsDescriptors.html
    .. image:: _static/descriptors/tonal.chords_count.png
        :height: 300px



tonal.hpcp_crest
-------------------------

::

    curl https://freesound.org/api/sounds/<sound_id>/analysis/tonal/hpcp_crest

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

    .. image:: _static/descriptors/tonal.hpcp_crest.mean.png
        :height: 300px



tonal.chords_histogram
-------------------------

::

    curl https://freesound.org/api/sounds/<sound_id>/analysis/tonal/chords_histogram

**Essentia Algorithm**

http://essentia.upf.edu/documentation/reference/streaming_ChordsDescriptors.html



tonal.chords_key
-------------------------

::

    curl https://freesound.org/api/sounds/<sound_id>/analysis/tonal/chords_key

**Essentia Algorithm**

http://essentia.upf.edu/documentation/reference/streaming_ChordsDescriptors.html



tonal.tuning_frequency
-------------------------

::

    curl https://freesound.org/api/sounds/<sound_id>/analysis/tonal/tuning_frequency

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



tonal.hpcp_peak_count
-------------------------

::

    curl https://freesound.org/api/sounds/<sound_id>/analysis/tonal/hpcp_peak_count

**Essentia Algorithm**

http://essentia.upf.edu/documentation/reference/streaming_PeakDetection.html
    .. image:: _static/descriptors/tonal.hpcp_peak_count.png
        :height: 300px



tonal.hpcp
-------------------------

::

    curl https://freesound.org/api/sounds/<sound_id>/analysis/tonal/hpcp

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



Sfx Descriptors
>>>>>>>>>>>>>>>>>>>>


sfx.temporal_decrease
-------------------------

::

    curl https://freesound.org/api/sounds/<sound_id>/analysis/sfx/temporal_decrease

**Essentia Algorithm**

http://essentia.upf.edu/documentation/reference/streaming_Decrease.html


**Stats**::


/max
/min
/mean


**Distribution in Freesound**

    .. image:: _static/descriptors/sfx.temporal_decrease.mean.png
        :height: 300px



sfx.inharmonicity
-------------------------

::

    curl https://freesound.org/api/sounds/<sound_id>/analysis/sfx/inharmonicity

**Essentia Algorithm**

http://essentia.upf.edu/documentation/reference/streaming_ Inharmonicity.html


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

    .. image:: _static/descriptors/sfx.inharmonicity.mean.png
        :height: 300px



sfx.pitch_min_to_total
-------------------------

::

    curl https://freesound.org/api/sounds/<sound_id>/analysis/sfx/pitch_min_to_total

**Essentia Algorithm**

http://essentia.upf.edu/documentation/reference/streaming_MinToTotal.html
    .. image:: _static/descriptors/sfx.pitch_min_to_total.png
        :height: 300px



sfx.tc_to_total
-------------------------

::

    curl https://freesound.org/api/sounds/<sound_id>/analysis/sfx/tc_to_total

**Essentia Algorithm**

http://essentia.upf.edu/documentation/reference/streaming_TCToTotal.html
    .. image:: _static/descriptors/sfx.tc_to_total.png
        :height: 300px



sfx.der_av_after_max
-------------------------

::

    curl https://freesound.org/api/sounds/<sound_id>/analysis/sfx/der_av_after_max

**Essentia Algorithm**

http://essentia.upf.edu/documentation/reference/streaming_DerivativeSFX.html


**Stats**::


/max
/min
/mean


**Distribution in Freesound**

    .. image:: _static/descriptors/sfx.der_av_after_max.mean.png
        :height: 300px



sfx.pitch_max_to_total
-------------------------

::

    curl https://freesound.org/api/sounds/<sound_id>/analysis/sfx/pitch_max_to_total

**Essentia Algorithm**

http://essentia.upf.edu/documentation/reference/streaming_MaxToTotal.html
    .. image:: _static/descriptors/sfx.pitch_max_to_total.png
        :height: 300px



sfx.temporal_spread
-------------------------

::

    curl https://freesound.org/api/sounds/<sound_id>/analysis/sfx/temporal_spread

**Essentia Algorithm**

http://essentia.upf.edu/documentation/reference/streaming_CentralMoments.html


**Stats**::


/max
/min
/mean


**Distribution in Freesound**

    .. image:: _static/descriptors/sfx.temporal_spread.mean.png
        :height: 300px



sfx.temporal_kurtosis
-------------------------

::

    curl https://freesound.org/api/sounds/<sound_id>/analysis/sfx/temporal_kurtosis

**Essentia Algorithm**

http://essentia.upf.edu/documentation/reference/streaming_CentralMoments.html


**Stats**::


/max
/min
/mean


**Distribution in Freesound**

    .. image:: _static/descriptors/sfx.temporal_kurtosis.mean.png
        :height: 300px



sfx.logattacktime
-------------------------

::

    curl https://freesound.org/api/sounds/<sound_id>/analysis/sfx/logattacktime

**Essentia Algorithm**

http://essentia.upf.edu/documentation/reference/streaming_LogAttackTime.html


**Stats**::


/max
/min
/mean


**Distribution in Freesound**

    .. image:: _static/descriptors/sfx.logattacktime.mean.png
        :height: 300px



sfx.temporal_centroid
-------------------------

::

    curl https://freesound.org/api/sounds/<sound_id>/analysis/sfx/temporal_centroid

**Essentia Algorithm**

http://essentia.upf.edu/documentation/reference/streaming_Centroid.html


**Stats**::


/max
/min
/mean


**Distribution in Freesound**

    .. image:: _static/descriptors/sfx.temporal_centroid.mean.png
        :height: 300px



sfx.tristimulus
-------------------------

::

    curl https://freesound.org/api/sounds/<sound_id>/analysis/sfx/tristimulus

**Essentia Algorithm**

http://essentia.upf.edu/documentation/reference/streaming_ Tristimulus.html


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

    .. image:: _static/descriptors/sfx.tristimulus.mean.000.png
        :height: 300px
    .. image:: _static/descriptors/sfx.tristimulus.mean.001.png
        :height: 300px
    .. image:: _static/descriptors/sfx.tristimulus.mean.002.png
        :height: 300px



sfx.max_der_before_max
-------------------------

::

    curl https://freesound.org/api/sounds/<sound_id>/analysis/sfx/max_der_before_max

**Essentia Algorithm**

http://essentia.upf.edu/documentation/reference/streaming_DerivativeSFX.html


**Stats**::


/max
/min
/mean


**Distribution in Freesound**

    .. image:: _static/descriptors/sfx.max_der_before_max.mean.png
        :height: 300px



sfx.strongdecay
-------------------------

::

    curl https://freesound.org/api/sounds/<sound_id>/analysis/sfx/strongdecay

**Essentia Algorithm**

http://essentia.upf.edu/documentation/reference/streaming_StrongDecay.html
    .. image:: _static/descriptors/sfx.strongdecay.png
        :height: 300px



sfx.pitch_centroid
-------------------------

::

    curl https://freesound.org/api/sounds/<sound_id>/analysis/sfx/pitch_centroid

**Essentia Algorithm**

http://essentia.upf.edu/documentation/reference/streaming_Centroid.html


**Stats**::


/max
/min
/mean


**Distribution in Freesound**

    .. image:: _static/descriptors/sfx.pitch_centroid.mean.png
        :height: 300px



sfx.duration
-------------------------

::

    curl https://freesound.org/api/sounds/<sound_id>/analysis/sfx/duration

**Essentia Algorithm**

http://essentia.upf.edu/documentation/reference/streaming_ Duration.html
    .. image:: _static/descriptors/sfx.duration.png
        :height: 300px



sfx.temporal_skewness
-------------------------

::

    curl https://freesound.org/api/sounds/<sound_id>/analysis/sfx/temporal_skewness

**Essentia Algorithm**

http://essentia.upf.edu/documentation/reference/streaming_CentralMoments.html


**Stats**::


/max
/min
/mean


**Distribution in Freesound**

    .. image:: _static/descriptors/sfx.temporal_skewness.mean.png
        :height: 300px



sfx.effective_duration
-------------------------

::

    curl https://freesound.org/api/sounds/<sound_id>/analysis/sfx/effective_duration

**Essentia Algorithm**

http://essentia.upf.edu/documentation/reference/streaming_EffectiveDuration.html


**Stats**::


/max
/min
/mean


**Distribution in Freesound**

    .. image:: _static/descriptors/sfx.effective_duration.mean.png
        :height: 300px



sfx.max_to_total
-------------------------

::

    curl https://freesound.org/api/sounds/<sound_id>/analysis/sfx/max_to_total

**Essentia Algorithm**

http://essentia.upf.edu/documentation/reference/streaming_MaxToTotal.html
    .. image:: _static/descriptors/sfx.max_to_total.png
        :height: 300px



sfx.oddtoevenharmonicenergyratio
-------------------------

::

    curl https://freesound.org/api/sounds/<sound_id>/analysis/sfx/oddtoevenharmonicenergyratio

**Essentia Algorithm**

http://essentia.upf.edu/documentation/reference/streaming_ OddToEvenHarmonicEnergyRatio.html


**Stats**::


/dmean2
/dmean
/mean
/max
/min


**Distribution in Freesound**

    .. image:: _static/descriptors/sfx.oddtoevenharmonicenergyratio.mean.png
        :height: 300px



sfx.pitch_after_max_to_before_max_energy_ratio
-------------------------

::

    curl https://freesound.org/api/sounds/<sound_id>/analysis/sfx/pitch_after_max_to_before_max_energy_ratio

**Essentia Algorithm**

http://essentia.upf.edu/documentation/reference/streaming_AfterMaxToBeforeMaxEnergyRatio.html
    .. image:: _static/descriptors/sfx.pitch_after_max_to_before_max_energy_ratio.png
        :height: 300px



