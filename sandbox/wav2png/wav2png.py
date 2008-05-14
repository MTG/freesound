import numpy, math, sys
import scikits.audiolab as audiolab
import Image, ImageDraw, ImageColor

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
        
        self.audio_file.seek(start)
        
        to_read = size if start + size <= self.frames else self.frames - start
        
        try:
            samples = self.audio_file.read_frames(to_read)
        except IOError:
            return numpy.zeroes(size) if resize_if_less else numpy.array([])

        if self.channels > 1:
            samples = samples[:,0]

        if resize_if_less and samples.shape[0] < size:
            samples = numpy.resize(samples, size)
            samples[to_read:] = 0
            
        return samples        


    def spectral_centroid(self, seek_point, spec_range=120.0):
        """ starting at seek_point read fft_size samples, and calculate the spectral centroid """
        
        samples = self.read(seek_point, self.fft_size, True)

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
            sc = (spectrum * self.spectrum_range).sum() / (energy * (length - 1))
            # arbitrary scaling to look the colors look good :)
            return (math.log(sc*512 + 1) / math.log(512 + 1), db_spectrum)


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


class ColorCreator(object):
    def __init__(self):
        self.num_colors = 1000
        self.colors = []

        for i in range(self.num_colors):
            self.colors.append( self.color_from_value(i/float(self.num_colors)) )
        
        self.palette = []
        colors = [  (0, 0, 0),
                    (58/4 * 128.0/256.0, 68/4 * 128.0/256.0,65/4 * 128.0/256.0, 12),
                    (80*230.0/256.0,100*230.0/256.0,153*230.0/256.0),
                    (90,180,100),
                    (224,224,44),
                    (255,60,30)]
    	
        for i in range(0,256):
            index = (i * (len(colors) - 1))/255.0
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
            	   
            self.palette.extend((int(r), int(g), int(b))) # grayscale wedge
            
    def get_palette(self):
        return self.palette

    def color_lookup(self, value):
        return self.colors[int( value*(self.num_colors - 1) )]

    def color_from_value(self, value):
        return ImageColor.getrgb("hsl(%d,%d%%,%d%%)" % (int( (1.0 - value) * 360 ), 80, 50))

def create_png():
    filename = sys.argv[1]
    
    fft_size = 2048
    
    image_width = 500
    image_height = 200
    
    audio_file = audiolab.sndfile(filename, 'read')
    samples_per_pixel = audio_file.get_nframes() / float(image_width)
    
    processor = AudioProcessor(audio_file, fft_size, numpy.hanning) 
    color_creator = ColorCreator()
    
    im_waveform = Image.new("RGB", (image_width, image_height))
    draw = ImageDraw.Draw(im_waveform)
    previous_x = 0
    previous_y = image_height / 2
    zero_line_color = ImageColor.getrgb("#ff0000")
    draw.line([0, image_height/2, image_width, image_height/2], zero_line_color )
    
    im_spectrogram = Image.new("P", (image_width, image_height))
    im_spectrogram.putpalette(color_creator.get_palette())
    y_to_bin = []
    f_min = 100.0
    f_max = 22050.0
    y_min = math.log(f_min)/math.log(10.0)
    y_max = math.log(f_max)/math.log(10.0)
    for y in range(image_height):
        y_inv = (image_height - 1.0 - y)/(image_height - 1.0) # between 1 and 0
        freq = math.pow(10.0, y_min + y_inv *(y_max - y_min))
        bin = freq / (audio_file.get_samplerate()/2.0) * (fft_size/2 + 1)
        y_to_bin.append(bin)
    pix = im_spectrogram.load()

    for x in range(image_width):
        
        seek_point = int(x * samples_per_pixel)
        next_seek_point = int( (x + 1) * samples_per_pixel)
        (spectral_centroid, db_spectrum) = processor.spectral_centroid(seek_point)
        peaks = processor.peaks(seek_point, next_seek_point)
    
        y1 = image_height * 0.5 - peaks[0] * image_height * 0.5
        y2 = image_height * 0.5 - peaks[1] * image_height * 0.5
        
        draw.line([previous_x, previous_y, x, y1, x, y2], color_creator.color_lookup(spectral_centroid))
    
        previous_x, previous_y = x, y2
        
        for y in range(image_height):
            
            bin = y_to_bin[y]
            
            if bin < db_spectrum.shape[0] - 1:
                int_bin = int(bin)
                alpha = bin - float(int_bin)
                db = (1.0 - alpha) * db_spectrum[int_bin] + alpha * db_spectrum[int_bin + 1]
                #col = color_creator.greyscale_lookup(db)

                pix[x,y] = int(255*db)
    
    im_waveform.save(filename + '_w.png')
    im_spectrogram.save(filename + '_s.png')

if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[2] == "profile":
        import hotshot
        from hotshot import stats
                prof = hotshot.Profile("stats")        prof.runcall(create_png)
        prof.close()
        
        s = stats.load("stats")
        s.sort_stats("time").print_stats()    else:
        create_png()