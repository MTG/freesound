#!/usr/bin/env python

#
# Freesound is (c) MUSIC TECHNOLOGY GROUP, UNIVERSITAT POMPEU FABRA
#
# Freesound is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# Freesound is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# Authors:
#     See AUTHORS file.
#


from past.utils import old_div
import math
import os
import re
import subprocess

import numpy
import pysndfile
from PIL import Image, ImageDraw

from .color_schemes import COLOR_SCHEMES, DEFAULT_COLOR_SCHEME_KEY
from utils.audioprocessing import get_sound_type


class AudioProcessingException(Exception):
    pass


class TestAudioFile:
    """A class that mimics pysndfile.PySndfile but generates noise instead of reading
    a wave file. Additionally it can be told to have a "broken" header and thus crashing
    in the middle of the file. Also useful for testing ultra-short files of 20 samples."""

    def __init__(self, num_frames, has_broken_header=False):
        self.seekpoint = 0
        self.nframes = num_frames
        self.samplerate = 44100
        self.channels = 1
        self.has_broken_header = has_broken_header

    def seek(self, seekpoint):
        self.seekpoint = seekpoint

    def read_frames(self, frames_to_read):
        if self.has_broken_header and self.seekpoint + frames_to_read > old_div(self.num_frames, 2):
            raise RuntimeError()

        num_frames_left = self.num_frames - self.seekpoint
        will_read = num_frames_left if num_frames_left < frames_to_read else frames_to_read
        self.seekpoint += will_read
        return numpy.random.random(will_read) * 2 - 1


def get_max_level(filename):
    max_value = 0
    buffer_size = 4096
    audio_file = pysndfile.PySndfile(filename, 'r')
    n_samples_left = audio_file.frames()

    while n_samples_left:
        to_read = min(buffer_size, n_samples_left)

        try:
            samples = audio_file.read_frames(to_read)
        except RuntimeError:
            # this can happen with a broken header
            break

        # convert to mono by selecting left channel only
        if audio_file.channels() > 1:
            samples = samples[:, 0]

        max_value = max(max_value, numpy.abs(samples).max())

        n_samples_left -= to_read

    audio_file.close()

    return max_value


class AudioProcessor:
    """
    The audio processor processes chunks of audio an calculates the spectrac centroid and the peak
    samples in that chunk of audio.
    """

    def __init__(self, input_filename, fft_size, window_function=numpy.hanning):
        max_level = get_max_level(input_filename)
        self.audio_file = pysndfile.PySndfile(input_filename, 'r')
        self.nframes = self.audio_file.frames()
        self.samplerate = self.audio_file.samplerate()
        self.fft_size = fft_size
        self.window = window_function(self.fft_size)
        self.spectrum_range = None
        self.lower = 100
        self.higher = 22050
        self.lower_log = math.log10(self.lower)
        self.higher_log = math.log10(self.higher)
        self.clip = lambda val, low, high: min(high, max(low, val))

        # figure out what the maximum value is for an FFT doing the FFT of a DC signal
        fft = numpy.fft.rfft(numpy.ones(fft_size) * self.window)
        max_fft = (numpy.abs(fft)).max()
        # set the scale to normalized audio and normalized FFT
        self.scale = (1.0 / max_level) / max_fft if max_level > 0 else 1

    def read(self, start, size, resize_if_less=False):
        """ read size samples starting at start, if resize_if_less is True and less than size
        samples are read, resize the array to size and fill with zeros """

        # number of zeros to add to start and end of the buffer
        add_to_start = 0
        add_to_end = 0

        if start < 0:
            # the first FFT window starts centered around zero
            if size + start <= 0:
                return numpy.zeros(size) if resize_if_less else numpy.array([])
            else:
                self.audio_file.seek(0)

                add_to_start = -start  # remember: start is negative!
                to_read = size + start

                if to_read > self.nframes:
                    add_to_end = to_read - self.nframes
                    to_read = self.nframes
        else:
            self.audio_file.seek(start)

            to_read = size
            if start + to_read >= self.nframes:
                to_read = self.nframes - start
                add_to_end = size - to_read

        try:
            samples = self.audio_file.read_frames(to_read)
        except RuntimeError:
            # this can happen for wave files with broken headers...
            return numpy.zeros(size) if resize_if_less else numpy.zeros(2)

        # convert to mono by selecting left channel only
        if self.audio_file.channels() > 1:
            samples = samples[:, 0]

        if resize_if_less and (add_to_start > 0 or add_to_end > 0):
            if add_to_start > 0:
                samples = numpy.concatenate((numpy.zeros(add_to_start), samples), axis=0)

            if add_to_end > 0:
                samples = numpy.resize(samples, size)
                samples[size - add_to_end:] = 0

        return samples

    def spectral_centroid(self, seek_point, spec_range=110.0):
        """ starting at seek_point read fft_size samples, and calculate the spectral centroid """

        samples = self.read(seek_point - old_div(self.fft_size, 2), self.fft_size, True)

        samples *= self.window
        fft = numpy.fft.rfft(samples)
        spectrum = self.scale * numpy.abs(fft)  # normalized abs(FFT) between 0 and 1
        length = numpy.float64(spectrum.shape[0])

        # scale the db spectrum from [- spec_range db ... 0 db] > [0..1]
        db_spectrum = old_div(((20 * (numpy.log10(spectrum + 1e-60))).clip(-spec_range, 0.0) + spec_range), spec_range)

        energy = spectrum.sum()
        spectral_centroid = 0

        if energy > 1e-60:
            # calculate the spectral centroid

            if self.spectrum_range is None:
                self.spectrum_range = numpy.arange(length)

            spectral_centroid = old_div((spectrum * self.spectrum_range).sum(), (energy * (length - 1))) * self.samplerate * 0.5

            # clip > log10 > scale between 0 and 1
            spectral_centroid = old_div((math.log10(self.clip(spectral_centroid, self.lower, self.higher)) - self.lower_log), (
                        self.higher_log - self.lower_log))

        return spectral_centroid, db_spectrum

    def peaks(self, start_seek, end_seek):
        """ read all samples between start_seek and end_seek, then find the minimum and maximum peak
        in that range. Returns that pair in the order they were found. So if min was found first,
        it returns (min, max) else the other way around. """

        # larger blocksizes are faster but take more mem...
        # Aha, Watson, a clue, a tradeof!
        block_size = 4096

        max_index = -1
        max_value = -1
        min_index = -1
        min_value = 1

        if start_seek < 0:
            start_seek = 0

        if end_seek > self.nframes:
            end_seek = self.nframes

        if end_seek <= start_seek:
            samples = self.read(start_seek, 1)
            return samples[0], samples[0]

        if block_size > end_seek - start_seek:
            block_size = end_seek - start_seek

        for i in range(start_seek, end_seek, block_size):
            samples = self.read(i, block_size)

            local_max_index = numpy.argmax(samples)
            local_max_value = samples[local_max_index]

            if local_max_value > max_value:
                max_value = local_max_value
                max_index = local_max_index

            local_min_index = numpy.argmin(samples)
            local_min_value = samples[local_min_index]

            if local_min_value < min_value:
                min_value = local_min_value
                min_index = local_min_index

        return (min_value, max_value) if min_index < max_index else (max_value, min_value)


def interpolate_colors(colors, flat=False, num_colors=256):
    """ given a list of colors, create a larger list of colors interpolating
    the first one. If flatten is True a list of numers will be returned. If
    False, a list of (r,g,b) tuples. num_colors is the number of colors wanted
    in the final list """

    palette = []

    for i in range(num_colors):
        index = old_div((i * (len(colors) - 1)), (num_colors - 1.0))
        index_int = int(index)
        alpha = index - float(index_int)

        if alpha > 0:
            r = (1.0 - alpha) * colors[index_int][0] + alpha * colors[index_int + 1][0]
            g = (1.0 - alpha) * colors[index_int][1] + alpha * colors[index_int + 1][1]
            b = (1.0 - alpha) * colors[index_int][2] + alpha * colors[index_int + 1][2]
        else:
            r = (1.0 - alpha) * colors[index_int][0]
            g = (1.0 - alpha) * colors[index_int][1]
            b = (1.0 - alpha) * colors[index_int][2]

        if flat:
            palette.extend((int(r), int(g), int(b)))
        else:
            palette.append((int(r), int(g), int(b)))

    return palette


class WaveformImage:
    """
    Given peaks and spectral centroids from the AudioProcessor, this class will construct
    a wavefile image which can be saved as PNG.
    """

    def __init__(self, image_width, image_height, color_scheme):
        if image_height % 2 == 0:
            print("WARNING: Height is not uneven, images look much better at uneven height")

        if isinstance(color_scheme, dict):
            self.color_scheme_to_use = color_scheme
        else:
            self.color_scheme_to_use = COLOR_SCHEMES.get(color_scheme, COLOR_SCHEMES[DEFAULT_COLOR_SCHEME_KEY])
        
        self.transparent_background = self.color_scheme_to_use.get('wave_transparent_background', False)
        if self.transparent_background:
            self.image = Image.new("RGBA", (image_width, image_height), (0, 0, 0, 0))
        else:
            background_color = self.color_scheme_to_use['wave_colors'][0]  # Only used if transparent_background is False
            self.image = Image.new("RGB", (image_width, image_height),  background_color)

        self.image_width = image_width
        self.image_height = image_height

        self.draw = ImageDraw.Draw(self.image)
        self.previous_x, self.previous_y = None, None

        colors = self.color_scheme_to_use['wave_colors'][1:]
        self.color_lookup = interpolate_colors(colors)
        self.pix = self.image.load()

    def draw_peaks(self, x, peaks, spectral_centroid):
        """ draw 2 peaks at x using the spectral_centroid for color """

        y1 = self.image_height * 0.5 - peaks[0] * (self.image_height - 4) * 0.5
        y2 = self.image_height * 0.5 - peaks[1] * (self.image_height - 4) * 0.5

        line_color = self.color_lookup[int(spectral_centroid * 255.0)]

        if self.previous_y is not None:
            self.draw.line([self.previous_x, self.previous_y, x, y1, x, y2], line_color)
        else:
            self.draw.line([x, y1, x, y2], line_color)

        self.previous_x, self.previous_y = x, y2

        self.draw_anti_aliased_pixels(x, y1, y2, line_color)

    def draw_anti_aliased_pixels(self, x, y1, y2, color):
        """ vertical anti-aliasing at y1 and y2 """
        
        y_max = max(y1, y2)
        y_max_int = int(y_max)
        alpha = y_max - y_max_int

        if alpha > 0.0 and alpha < 1.0 and y_max_int + 1 < self.image_height:
            if not self.transparent_background:
                current_pix = self.pix[x, y_max_int + 1]
                r = int((1 - alpha) * current_pix[0] + alpha * color[0])
                g = int((1 - alpha) * current_pix[1] + alpha * color[1])
                b = int((1 - alpha) * current_pix[2] + alpha * color[2])
                self.pix[x, y_max_int + 1] = (r, g, b)
            else:
                # If using transparent background, don't do anti-aliasing
                self.pix[x, y_max_int + 1] = (color[0], color[1], color[2], 255)
                

        y_min = min(y1, y2)
        y_min_int = int(y_min)
        alpha = 1.0 - (y_min - y_min_int)

        if alpha > 0.0 and alpha < 1.0 and y_min_int - 1 >= 0:
            if not self.transparent_background:
                r = int((1 - alpha) * current_pix[0] + alpha * color[0])
                g = int((1 - alpha) * current_pix[1] + alpha * color[1])
                b = int((1 - alpha) * current_pix[2] + alpha * color[2])
                self.pix[x, y_min_int - 1] = (r, g, b)
            else:
                # If using transparent background, don't do anti-aliasing
                self.pix[x, y_max_int + 1] = (color[0], color[1], color[2], 255)

    def save(self, filename):
        # draw a zero "zero" line
        a = self.color_scheme_to_use.get('wave_zero_line_alpha', 0)
        if a:
            for x in range(self.image_width):
                self.pix[x, old_div(self.image_height, 2)] = tuple([p + a for p in self.pix[x, old_div(self.image_height, 2)]])

        self.image.save(filename)


class SpectrogramImage:
    """
    Given spectra from the AudioProcessor, this class will construct a wavefile image which
    can be saved as PNG.
    """

    def __init__(self, image_width, image_height, fft_size, color_scheme):
        self.image_width = image_width
        self.image_height = image_height
        self.fft_size = fft_size

        self.image = Image.new("RGB", (image_height, image_width))
        if isinstance(color_scheme, dict):
            spectrogram_colors = color_scheme['spec_colors']
        else:
            spectrogram_colors = COLOR_SCHEMES.get(color_scheme, COLOR_SCHEMES[DEFAULT_COLOR_SCHEME_KEY])['spec_colors']
        self.palette = interpolate_colors(spectrogram_colors)

        # generate the lookup which translates y-coordinate to fft-bin
        self.y_to_bin = []
        f_min = 100.0
        f_max = 22050.0
        y_min = math.log10(f_min)
        y_max = math.log10(f_max)
        for y in range(self.image_height):
            freq = math.pow(10.0, y_min + old_div(y, (image_height - 1.0)) * (y_max - y_min))
            bin = freq / 22050.0 * (old_div(self.fft_size, 2) + 1)

            if bin < old_div(self.fft_size, 2):
                alpha = bin - int(bin)

                self.y_to_bin.append((int(bin), alpha * 255))

        # this is a bit strange, but using image.load()[x,y] = ... is
        # a lot slower than using image.putadata and then rotating the image
        # so we store all the pixels in an array and then create the image when saving
        self.pixels = []

    def draw_spectrum(self, x, spectrum):
        # for all frequencies, draw the pixels
        for (index, alpha) in self.y_to_bin:
            self.pixels.append(self.palette[int((255.0 - alpha) * spectrum[index] + alpha * spectrum[index + 1])])

        # if the FFT is too small to fill up the image, fill with black to the top
        for y in range(len(self.y_to_bin), self.image_height):
            self.pixels.append(self.palette[0])

    def save(self, filename, quality=80):
        self.image.putdata(self.pixels)
        self.image.transpose(Image.ROTATE_90).save(filename, quality=quality)


def create_wave_images(input_filename, output_filename_w, output_filename_s, image_width, image_height, fft_size,
                       progress_callback=None, color_scheme=None, use_transparent_background=False):
    """
    Utility function for creating both wavefile and spectrum images from an audio input file.
    :param input_filename: input audio filename (must be PCM)
    :param output_filename_w: output filename for waveform image (must end in .png)
    :param output_filename_s: output filename for spectrogram image (must end in .jpg)
    :param image_width: width of both spectrogram and waveform images
    :param image_height: height of both spectrogram and waveform images
    :param fft_size: size of the FFT computed for the spectrogram image
    :param progress_callback: function to iteratively call while images are being created. Will be called every 1%,
                                with parameters (current_position, width)
    :param color_scheme: color scheme to use for the generated images (defaults to Freesound2 color scheme)
    """
    processor = AudioProcessor(input_filename, fft_size, numpy.hanning)
    samples_per_pixel = processor.nframes / float(image_width)

    waveform = WaveformImage(image_width, image_height, color_scheme)
    spectrogram = SpectrogramImage(image_width, image_height, fft_size, color_scheme)

    for x in range(image_width):

        if progress_callback and x % (old_div(image_width, 100)) == 0:
            progress_callback(x, image_width)

        seek_point = int(x * samples_per_pixel)
        next_seek_point = int((x + 1) * samples_per_pixel)

        (spectral_centroid, db_spectrum) = processor.spectral_centroid(seek_point)
        peaks = processor.peaks(seek_point, next_seek_point)

        waveform.draw_peaks(x, peaks, spectral_centroid)
        spectrogram.draw_spectrum(x, db_spectrum)

    if progress_callback:
        progress_callback(image_width, image_width)

    waveform.save(output_filename_w)
    spectrogram.save(output_filename_s)


class NoSpaceLeftException(Exception):
    pass


def convert_to_pcm(input_filename, output_filename, use_ffmpeg_for_unknown_type=False):
    """
    converts any audio file type to pcm audio
    """
    if not os.path.exists(input_filename):
        raise AudioProcessingException(f"file {input_filename} does not exist")
    sound_type = get_sound_type(input_filename)

    if sound_type in ["mp3", "ogg", "flac", "m4a"]:
        if sound_type == "mp3":
            cmd = ["lame", "--decode", input_filename, output_filename]
            error_messages = ["WAVE file contains 0 PCM samples"]
        elif sound_type == "ogg":
            cmd = ["oggdec", input_filename, "-o", output_filename]
            error_messages = []
        elif sound_type == "flac":
            cmd = ["flac", "-f", "-d", "-s", "-o", output_filename, input_filename]
            error_messages = []
        elif sound_type == "m4a":
            cmd = ["faad", "-o", output_filename, input_filename]
            error_messages = ["Unable to find correct AAC sound track in the MP4 file",
                            "Error: Bitstream value not allowed by specification",
                            "Error opening file"]
   
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (stdout, stderr) = process.communicate()
        stdout = stdout.decode(errors='ignore')
        stderr = stderr.decode(errors='ignore')
        
        # If external process returned an error (return code != 0) or the expected PCM file does not
        # exist, raise exception
        if process.returncode != 0 or not os.path.exists(output_filename):
            if "No space left on device" in stderr + " " + stdout:
                raise NoSpaceLeftException
            raise AudioProcessingException("failed converting to pcm data:\n"
                                        + " ".join(cmd) + "\n" + stderr + "\n" + stdout)
        
        # If external process apparently returned no error (return code = 0) but we see some errors from our list of
        # known errors have been printed in stderr, raise an exception as well
        if any([error_message in stderr for error_message in error_messages]):
            raise AudioProcessingException("failed converting to pcm data:\n"
                                        + " ".join(cmd) + "\n" + stderr + "\n" + stdout)
    else:
        if use_ffmpeg_for_unknown_type:
            convert_using_ffmpeg(input_filename, output_filename)
        else:
            return False
    return True


def stereofy_and_find_info(stereofy_executble_path, input_filename, output_filename):
    """
    converts a pcm wave file to two channel, 16 bit integer
    """

    if not os.path.exists(input_filename):
        raise AudioProcessingException(f"file {input_filename} does not exist")

    cmd = [stereofy_executble_path, "--input", input_filename, "--output", output_filename]

    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    (stdout, stderr) = process.communicate()
    stdout = stdout.decode(errors='ignore')
    stderr = stderr.decode(errors='ignore')

    if process.returncode != 0 or not os.path.exists(output_filename):
        if "No space left on device" in stderr + " " + stdout:
            raise NoSpaceLeftException
        raise AudioProcessingException(
            "failed calling stereofy data:\n" + " ".join(cmd) + "\n" + stderr + "\n" + stdout)

    stdout = (stdout + " " + stderr).replace("\n", " ")

    duration = 0
    m = re.match(r".*#duration (?P<duration>[\d\.]+).*", stdout)
    if m is not None:
        duration = float(m.group("duration"))

    channels = 0
    m = re.match(r".*#channels (?P<channels>\d+).*", stdout)
    if m is not None:
        channels = float(m.group("channels"))

    samplerate = 0
    m = re.match(r".*#samplerate (?P<samplerate>\d+).*", stdout)
    if m is not None:
        samplerate = float(m.group("samplerate"))

    bitdepth = 0
    m = re.match(r".*#bitdepth (?P<bitdepth>\d+).*", stdout)
    if m is not None:
        bitdepth = float(m.group("bitdepth"))

    # NOTE: we do not return bitrate here as we compute it when storing audio info fields in the sound model
    return dict(duration=duration, channels=channels, samplerate=samplerate, bitdepth=bitdepth)


def convert_to_mp3(input_filename, output_filename, quality=70):
    """
    converts the incoming wave file to a mp3 file
    """

    if not os.path.exists(input_filename):
        raise AudioProcessingException(f"file {input_filename} does not exist")

    command = ["lame", "--silent", "--abr", str(quality), input_filename, output_filename]

    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    (stdout, _) = process.communicate()
    stdout = stdout.decode(errors='ignore')

    if process.returncode != 0 or not os.path.exists(output_filename):
        raise AudioProcessingException(stdout)


def convert_to_ogg(input_filename, output_filename, quality=1):
    """
    converts the incoming wave file to n ogg file
    """

    if not os.path.exists(input_filename):
        raise AudioProcessingException(f"file {input_filename} does not exist")

    command = ["oggenc", "-q", str(quality), input_filename, "-o", output_filename]

    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    (stdout, _) = process.communicate()
    stdout = stdout.decode(errors='ignore')
    
    if process.returncode != 0 or not os.path.exists(output_filename):
        raise AudioProcessingException(stdout)


def convert_using_ffmpeg(input_filename, output_filename, force_output_format=False, mono_out=False):
    """
    converts the incoming wave file to 16bit, 44kHz pcm using fffmpeg
    unlike the convert_to_pcm function above, this one does not try to preserve
    the original sample rate and bit depth.
    """

    if not os.path.exists(input_filename):
        raise AudioProcessingException(f"file {input_filename} does not exist")

    command = ["ffmpeg", "-y", "-i", input_filename]
    if force_output_format:
        command += ["-acodec", "pcm_s16le", "-ar", "44100"]
    if mono_out:
        command += ['-ac', '1']
    command += [output_filename]

    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    (stdout, stderr) = process.communicate()
    stdout = stdout.decode(errors='ignore')
    stderr = stderr.decode(errors='ignore')
    if process.returncode != 0 or not os.path.exists(output_filename):
        raise AudioProcessingException(f"ffmpeg returned an error\nstdout: {stdout} \nstderr: {stderr}")
