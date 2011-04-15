#!/usr/bin/env python
from processing import create_wave_images, AudioProcessingException
import optparse
import sys

parser = optparse.OptionParser("usage: %prog [options] input-filename", conflict_handler="resolve")
parser.add_option("-a", "--waveout", action="store", dest="output_filename_w", type="string", help="output waveform image (default input filename + _w.png)")
parser.add_option("-s", "--specout", action="store", dest="output_filename_s", type="string", help="output spectrogram image (default input filename + _s.jpg)")
parser.add_option("-w", "--width", action="store", dest="image_width", type="int", help="image width in pixels (default %default)")
parser.add_option("-h", "--height", action="store", dest="image_height", type="int", help="image height in pixels (default %default)")
parser.add_option("-f", "--fft", action="store", dest="fft_size", type="int", help="fft size, power of 2 for increased performance (default %default)")
parser.add_option("-p", "--profile", action="store_true", dest="profile", help="run profiler and output profiling information")

parser.set_defaults(output_filename_w=None, output_filename_s=None, image_width=500, image_height=171, fft_size=2048)

(options, args) = parser.parse_args()

if len(args) == 0:
    parser.print_help()
    parser.error("not enough arguments")
   
    if len(args) > 1 and (options.output_filename_w != None or options.output_filename_s != None):
        parser.error("when processing multiple files you can't define the output filename!")
 
def progress_callback(percentage):
    sys.stdout.write(str(percentage) + "% ")
    sys.stdout.flush()
   
    # process all files so the user can use wildcards like *.wav
for input_file in args:
    
    output_file_w = options.output_filename_w or input_file + "_w.png"
    output_file_s = options.output_filename_s or input_file + "_s.jpg"
    
    args = (input_file, output_file_w, output_file_s, options.image_width, options.image_height, options.fft_size, progress_callback)

    print "processing file %s:\n\t" % input_file,

    if not options.profile:
        try:
            create_wave_images(*args)
        except AudioProcessingException, e:
            print "Error running wav2png: ", e
    else:
        from hotshot import stats
        import hotshot

        prof = hotshot.Profile("stats")
        prof.runcall(create_wave_images, *args)
        prof.close()
        
        print "\n---------- profiling information ----------\n"
        s = stats.load("stats")
        s.strip_dirs()
        s.sort_stats("time")
        s.print_stats(30)
    
    print