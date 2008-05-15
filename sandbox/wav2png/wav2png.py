import numpy, math, sys
import scikits.audiolab as audiolab
import Image, ImageDraw, ImageColor

class TestAudioFile(object):
    def __init__(self, num_frames, has_broken_header=False):
        self.seekpoint = 0
        self.num_frames = num_frames
        self.has_broken_header = has_broken_header

    def seek(self, seekpoint):
        self.seekpoint = seekpoint

    def get_nframes(self):
        return self.num_frames

    def get_samplerate(self):
        return 44100

    def get_channels(self):
        return 1

    def read_frames(self, frames_to_read):
        if self.has_broken_header and self.seekpoint + frames_to_read > self.num_frames / 2:
            raise IOError()

        num_frames_left = self.num_frames - self.seekpoint
        will_read = num_frames_left if num_frames_left < frames_to_read else frames_to_read
        self.seekpoint += will_read
        return numpy.random.random(will_read)*2 - 1 


class AudioProcessor(object):
    def __init__(self, audio_file, fft_size, window_function=numpy.ones):
        self.fft_size = fft_size
        self.window = window_function(self.fft_size)
        self.audio_file = audio_file
        self.frames = audio_file.get_nframes()
        self.samplerate = audio_file.get_samplerate()
        self.channels = audio_file.get_channels()
        self.spectrum_range = None
    

    def read(self, start, size, resize_if_less=False):
        """ read size samples starting at start, if resize_if_less is True and less than size
        samples are read, resize the array to size and fill with zeros """
        
        add_to_start = 0
        add_to_end = 0
        
        if start < 0:
            if size + start <= 0:
                return numpy.zeros(size) if resize_if_less else numpy.array([])
            else:
                self.audio_file.seek(0)

                add_to_start = -start # remember: start is negative!
                to_read = size + start

                if to_read > self.frames:
                    add_to_end = to_read - self.frames
                    to_read = self.frames
        else:
            self.audio_file.seek(start)
        
            to_read = size
            if start + to_read >= self.frames:
                to_read = self.frames - start
                add_to_end = size - to_read
        
        try:
            samples = self.audio_file.read_frames(to_read)
        except IOError:
            return numpy.zeros(size) if resize_if_less else numpy.zeros(2)

        if self.channels > 1:
            samples = samples[:,0]

        if resize_if_less and (add_to_start > 0 or add_to_end > 0):
            if add_to_start > 0:
                samples = numpy.concatenate((numpy.zeros(add_to_start), samples), axis=1)
            
            if add_to_end > 0:
                samples = numpy.resize(samples, size)
                samples[size - add_to_end:] = 0
        
        if resize_if_less:
            assert samples.shape[0] == size
            
        return samples        


    def spectral_centroid(self, seek_point, spec_range=120.0):
        """ starting at seek_point read fft_size samples, and calculate the spectral centroid """
        
        samples = self.read(seek_point - self.fft_size/2, self.fft_size, True)

        samples *= self.window
        fft = numpy.fft.fft(samples)
        spectrum = numpy.abs(fft[:fft.shape[0] / 2 + 1]) / float(self.fft_size)
        length = numpy.float64(spectrum.shape[0])
        
        if self.spectrum_range == None:
            self.spectrum_range = numpy.arange(length)
        
        energy = spectrum.sum()
        
        db_spectrum = ((20*(numpy.log10(spectrum + 1e-30))).clip(-spec_range, 0.0) + spec_range)/spec_range
        
        if energy < 1e-20:
            return (0, db_spectrum)
        else:
            sc = (spectrum * self.spectrum_range).sum() / (energy * (length - 1)) * self.samplerate*0.5
            
            if sc < 100:
                sc = 100
                
            if sc > 22050:
                sc = 22050
            
            # arbitrary scaling to look the colors look good :)
            return (math.log(sc) - math.log(100)) / (math.log(22050) - math.log(100)), db_spectrum


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
    
        if end_seek > self.frames:
            end_seek = self.frames
    
        if block_size > end_seek - start_seek:
            block_size = end_seek - start_seek
            
        if block_size <= 1:
            samples = self.read(start_seek, 1)
            return samples[0], samples[0]
        elif block_size == 2:
            samples = self.read(start_seek, True)
            return samples[0], samples[1]
        
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
        index = (i * (len(colors) - 1))/(num_colors - 1.0)
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
    

class WaveformImage(object):
    def __init__(self, image_width, image_height):
        self.image = Image.new("RGB", (image_width, image_height))
        
        self.image_width = image_width
        self.image_height = image_height
        
        self.draw = ImageDraw.Draw(self.image)
        self.previous_x, self.previous_y = None, None
        
        colors = [  
                    (50,0,200),
                    (0,220,80),
                    (255,224,0),
                 ]
        
        # this line gets the old "screaming" colors back...
        # colors = [self.color_from_value(value/29.0) for value in range(0,30)]
        
        self.color_lookup = interpolate_colors(colors)
        self.pix = self.image.load()
        

    def color_from_value(self, value):
        """ given a value between 0 and 1, return an (r,g,b) tuple """

        return ImageColor.getrgb("hsl(%d,%d%%,%d%%)" % (int( (1.0 - value) * 360 ), 80, 50))
        
        
    def draw_peaks(self, x, peaks, spectral_centroid):
        """ draw 2 peaks at x using the spectral_centroid for color """

        y1 = self.image_height * 0.5 - peaks[0] * self.image_height * 0.5
        y2 = self.image_height * 0.5 - peaks[1] * self.image_height * 0.5
        
        line_color = self.color_lookup[int(spectral_centroid*255.0)]
        
        if self.previous_y != None:
            self.draw.line([self.previous_x, self.previous_y, x, y1, x, y2], line_color)
        else:
            self.draw.line([x, y1, x, y2], line_color)
    
        self.previous_x, self.previous_y = x, y2
        
        #self.draw_anti_aliased_pixels(x, y1, y2, line_color)
    
    
    def draw_anti_aliased_pixels(self, x, y1, y2, color):
        """ vertical anti-aliasing at y1 and y2 """

        y_max = max(y1, y2)
        y_max_int = int(y_max)
        alpha = y_max - y_max_int
        
        if alpha > 0.0 and alpha < 1.0 and y_max_int + 1 < self.image_height:
            current_pix = self.pix[x, y_max_int + 1]
                
            r = int((1-alpha)*current_pix[0] + alpha*color[0])
            g = int((1-alpha)*current_pix[1] + alpha*color[1])
            b = int((1-alpha)*current_pix[2] + alpha*color[2])
            
            self.pix[x, y_max_int + 1] = (r,g,b)
            
        y_min = min(y1, y2)
        y_min_int = int(y_min)
        alpha = 1.0 - (y_min - y_min_int)
        
        if alpha > 0.0 and alpha < 1.0 and y_min_int - 1 >= 0:
            current_pix = self.pix[x, y_min_int - 1]
                
            r = int((1-alpha)*current_pix[0] + alpha*color[0])
            g = int((1-alpha)*current_pix[1] + alpha*color[1])
            b = int((1-alpha)*current_pix[2] + alpha*color[2])
            
            self.pix[x, y_min_int - 1] = (r,g,b)
            
            
    def save(self, filename):
        # draw a zer "zero" line
        for x in range(self.image_width):
            rgb = self.pix[x, self.image_height/2]
            if rgb == (0,0,0):
                rgb = (20,20,20)
            self.pix[x, self.image_height/2] = (rgb[0]*3, rgb[1]*3, rgb[2]*3)

        #self.draw.line([0, self.image_height/2, self.image_width, self.image_height/2], (255,255,255) )
        self.image.save(filename)
        
        
class SpectrogramImage(object):
    def __init__(self, image_width, image_height, fft_size):
        self.image = Image.new("P", (image_height, image_width))
        
        self.image_width = image_width
        self.image_height = image_height
        self.fft_size = fft_size
        
        colors = [  (0, 0, 0),
                    (58/4,68/4,65/4),
                    (80/2,100/2,153/2),
                    (90,180,100),
                    (224,224,44),
                    (255,60,30),
                    (255,255,255) ]
        
        self.image.putpalette(interpolate_colors(colors, True))

        # generate the lookup which translates y-coordinate to fft-bin
        self.y_to_bin = []
        f_min = 100.0
        f_max = 22050.0
        y_min = math.log(f_min)/math.log(10.0)
        y_max = math.log(f_max)/math.log(10.0)
        for y in range(self.image_height):
            freq = math.pow(10.0, y_min + y / (image_height - 1.0) *(y_max - y_min))
            bin = freq / 22050.0 * (self.fft_size/2 + 1)

            if bin < self.fft_size/2:
                alpha = bin - int(bin)
                
                self.y_to_bin.append((int(bin), alpha * 255))
           
        self.pixels = []
            
    def draw_spectrum(self, x, spectrum):
        for (index, alpha) in self.y_to_bin:
            self.pixels.append( int( ((255.0-alpha) * spectrum[index] + alpha * spectrum[index + 1] )) )
            
        for y in range(len(self.y_to_bin), self.image_height):
            self.pixels.append(0)

    def save(self, filename):
        self.image.putdata(self.pixels)
        self.image.transpose(Image.ROTATE_90).save(filename)


def create_png():
    filename = sys.argv[1]
    
    fft_size = 2048
    
    image_width = 500
    image_height = 170
    
    audio_file = audiolab.sndfile(filename, 'read')
    #audio_file = TestAudioFile(44100, False)

    samples_per_pixel = audio_file.get_nframes() / float(image_width)
    processor = AudioProcessor(audio_file, fft_size, numpy.hanning)
    
    waveform = WaveformImage(image_width, image_height)
    spectrogram = SpectrogramImage(image_width, image_height, fft_size)
    
    for x in range(image_width):
        seek_point = int(x * samples_per_pixel)
        next_seek_point = int( (x + 1) * samples_per_pixel)
        
        (spectral_centroid, db_spectrum) = processor.spectral_centroid(seek_point)
        peaks = processor.peaks(seek_point, next_seek_point)
        
        waveform.draw_peaks(x, peaks, spectral_centroid)
        spectrogram.draw_spectrum(x, db_spectrum)
        
    
    waveform.save(filename + '_w.png')
    spectrogram.save(filename + '_s.png')


if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[2] == "profile":
        import hotshot
        from hotshot import stats
        prof = hotshot.Profile("stats")
        prof.runcall(create_png)
        prof.close()
        
        s = stats.load("stats")
        s.sort_stats("time").print_stats()
    else:
        create_png()
