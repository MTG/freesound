#!/usr/bin/env python

from processing import *
import tempfile

large_size = (358, 169)
small_size = (80, 41)

def dofs1(filename, mp3Preview, image, smallImage):
    print "creating preview etc for file", filename

    hande, temp_filename = tempfile.mkstemp(".wav")
    
    try:
        convert_to_wav(filename, temp_filename)
    except AudioProcessingException, e:
        print "failed to convert file to wav"
        print e

        try:
            os.remove(temp_filename)
        except:
            pass
        
        sys.exit(1)

    try:
        create_wave_png_fs1(temp_filename, image, *large_size)
        create_wave_png_fs1(temp_filename, smallImage, *small_size)
        
        convert_to_mp3(temp_filename, mp3Preview)
    except AudioProcessingException, e:
        print "failed to create pngs or preview"
        print e

        try:
            os.remove(temp_filename)
        except:
            pass
        
        sys.exit(1)
    
    os.remove(temp_filename)
    sys.exit(0)

dofs1(*sys.argv[2:5])