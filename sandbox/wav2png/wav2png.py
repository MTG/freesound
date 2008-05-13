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
        self.spectrum_range = None;
    
    def read(self, start, size, resize_if_less=False):
        self.audio_file.seek(start)
        
        to_read = size if start + size <= self.frames else self.frames - start
        
        try:
            samples = self.audio_file.read_frames(to_read)
        except IOError:
            return numpy.zeroes(size) if resize_if_less else numpy.array([])

        if self.channels > 1:
            samples = samples[:,0]

        return samples        

    def spectral_centroid(self, seek_point):
        samples = self.read(seek_point, self.fft_size, True)

        samples *= self.window
        fft = numpy.fft.fft(samples)
        spectrum = numpy.abs(fft[:fft.shape[0] / 2 + 1])
        length = numpy.float64(spectrum.shape[0])
        
        if self.spectrum_range == None:
            self.spectrum_range = numpy.arange(length)
        
        energy = spectrum.sum()
    
        if energy < 1e-20:
            return 0
        else:
            sc = (spectrum * self.spectrum_range).sum() / (energy * (length - 1))
            # arbitrary scaling to look the colors look good :)
            return math.log(sc*512 + 1) / math.log(512 + 1)

    def peaks(self, start_seek, end_seek):
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


def color_from_value(value):
    h = int( (1.0 - value) * 360 )
    s = 80;
    v = 50;
    return ImageColor.getrgb("hsl(%d,%d%%,%d%%)" % (h,s,v))
    

def create_png():
    filename = sys.argv[1]
    
    fft_size = 2048
    
    image_width = 400
    image_height = 150
    
    audio_file = audiolab.sndfile(filename, 'read')
    
    frames = audio_file.get_nframes()
    samplerate = audio_file.get_samplerate()
    samples_per_pixel = frames / float(image_width)
    processor = AudioProcessor(audio_file, fft_size, numpy.hanning) 
    
    im = Image.new("RGB", (image_width, image_height))
    draw = ImageDraw.Draw(im)
    
    previous_x = 0
    previous_y = image_height / 2
    
    for x in range(image_width):
        
        seek_point = int(x * samples_per_pixel)
        next_seek_point = int( (x + 1) * samples_per_pixel)
        c = processor.spectral_centroid(seek_point)
        p = processor.peaks(seek_point, next_seek_point)
    
        y1 = image_height * 0.5 - p[0] * image_height * 0.5
        y2 = image_height * 0.5 - p[1] * image_height * 0.5
    
        draw.line([previous_x, previous_y, x, y1, x, y2], color_from_value(c))
    
        previous_x, previous_y = x, y2
    
    im.save(filename + '.png')

if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[2] == "profile":
        import hotshot
        from hotshot import stats
                prof = hotshot.Profile("stats")        prof.runcall(create_png)
        prof.close()
        
        s = stats.load("stats")
        s.sort_stats("time").print_stats()    else:
        create_png()