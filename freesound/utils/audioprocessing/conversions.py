if __name__ == "__main__":
    import sys
    
    convert_to_wav(sys.argv[1], sys.argv[2])

    """
    for index, filename in enumerate(sys.argv[1:]):
        print index,
        
        try:
            wav_filename = os.path.join("wavs", os.path.splitext(os.path.basename(filename))[0]) + '.wav'
            convert_to_wav(filename, wav_filename)

            info = audio_info(wav_filename)
            if not ( info["bits"] == 16 and info["samplerate"] == 44100 and info["channels"] == 2 and info["duration"] > 0 ):
                print
                print os.path.basename(filename), "has wrong wav stats"

            os.remove(wav_filename)
        except AudioProcessingException, e:
            print
            print os.path.basename(filename)
            print "error converting:", e
            
        try:
            info = audio_info(filename)
            for (k,v) in info.items():
                print k,"->", v, " ",
            print
        except AudioProcessingException, e:
            print
            print os.path.basename(filename)
            print "error extracting info:", e
    """