#!/usr/bin/python
#
# functions related to AudioClas computing

AUDIOCLAS_EXECUTABLE_SPECTRAL_CENTROID	= '/freesound/scripts/audioclas/bin/audioclas_spectral_centroid'
AUDIOCLAS_EXECUTABLE			= '/freesound/scripts/audioclas/bin/audioclas'
AUDIOCLAS_CONFIGFILE			= '/freesound/scripts/audioclas/bin/audioclas_sfx.conf'
AUDIOCLAS_CONFIGFILE_SPECTRALCENTROID	= '/freesound/scripts/audioclas/bin/spectralCentroid.conf'
AUDIOCLAS_SIGNATURE_DECRYPT		= '/freesound/scripts/audioclas/bin/decryptsig'

STEREOFY_EXECUTABLE			= '/freesound/utils/stereofy/stereofy-static'
WAV2PNG					= '/freesound/utils/wav2png/wav2png-static'

import os
import tempfile
import wave
import sys
import subprocess, shlex

def call(cmd):
	return subprocess.call(shlex.split(cmd))

def cleanup():
	print "cleaning up temp files..."
	files = os.listdir('/tmp/')
	for file in files:
		if file.startswith('AUDIOCLAS_'):
			os.remove('/tmp/%s' % file)


def exitAudioclas(error):
	if error:
		print "exiting with panic :-)"
		cleanup()
		sys.exit(-1)
	else:
		print "all done..."
		cleanup()
		sys.exit(0)


def create_preview(filenameIn, filenameOut):
	print "creating mp3 preview"
#	filenameOut = os.path.splitext( filenameOut )[0] # TODO changer ici et en dessous
	cmd = 'lame --quiet --resample 44.1 --abr 64 %s %s' % (filenameIn, filenameOut)
	print "\tcmd = %s" % cmd

	if call(cmd) != 0:
		print "creating mp3 preview FAILED"
		return -1
	else:
		return 0


def convert_to_wav(audiofile, outfile, samplerate,mp3Preview):
	name, extension = os.path.splitext(audiofile)

	tmpfile = tempfile.mkstemp('.wav', 'AUDIOCLAS_')[1]
	tmpfile2 = tempfile.mkstemp('.wav', 'AUDIOCLAS_')[1]
	tmpfile3 = tempfile.mkstemp('.wav', 'AUDIOCLAS_')[1]

	extension = extension.lower()

	# First decompress to wav, using appropriate decoder (sox if none found)
	if extension == ".mp3":
		cmd = 'mpg321 "%s" -w "%s"' % (audiofile, tmpfile)

	elif extension == ".ogg":
		cmd = 'oggdec "%s" -o "%s"' % (audiofile, tmpfile)

	elif extension in [".flac", ".fla"]:
		cmd = 'flac -f -d -s -o %s %s' % (tmpfile, audiofile)

	elif extension in [ ".aiff", ".aif", ".wav", ".au" ]:
		cmd = 'sndfile-convert -pcm16 "%s" "%s"' % (audiofile, tmpfile)

	else:
		cmd = 'sox "%s" "%s"' % (audiofile, tmpfile)

	print "converting to wav"
	print "\tcmd = %s" % cmd

	# Convert to WAV or disired format anyway
	if  call(cmd) != 0:
		# Do a last-ditch try with SOX...
		cmd = 'sox "%s" "%s"' % (audiofile, tmpfile)
		print "conversion failed, trying alternative method with sox"
		print "\tcmd = %s" % cmd
		if call(cmd) != 0:
			print "alternative method: FAILED"
			return -1

	# Change to equal or less than 2 channels
	cmd = '%s -i %s -o %s' % (STEREOFY_EXECUTABLE, tmpfile, tmpfile2)
	print "Conversion n-channel 2 stereo"
	print "\tcmd = %s" % cmd
	if call(cmd) != 0:
		print "conversion n-channel 2 stereo: FAILED"
		return -1

	# Create mp3 preview
	if create_preview(tmpfile2,mp3Preview) != 0:
		return -1

	# Resample and change to mono
	cmd = '/freesound/utils/libsamplerate/examples/sndfile-resample -to %s -c 2 %s %s' % (samplerate, tmpfile2, outfile)
	print "Resampling, Secret Rabbit Code Powered..."
	print "cmd = %s" % cmd;

	if call(cmd) != 0:
		print "downsampling FAILED"
		return -1

	print "Conversion and mp3 preview created."

	return 0


#def compute(mode, filename, descriptorFilename):
def compute(mode, filename, mp3Preview, image, smallImage,descriptorFile,colorFile):
	# first convert our audiofile to a temporary wav file
	tmpfile = tempfile.mkstemp('.wav', 'AUDIOCLAS_')[1]
	if mode == "-all":
		tmpfile2 = tempfile.mkstemp('.dat', 'AUDIOCLAS_')[1]
		spectralTempfile = tempfile.mkstemp('.tmp','AUDIOCLAS_')[1]

	# convert to wave file at channels and freq, no matter what original file was
	if convert_to_wav(filename, tmpfile, 44100,mp3Preview) != 0:
		exitAudioclas(True)

	# calculate descriptors
	cmd = '%s %s %s %s' % (AUDIOCLAS_EXECUTABLE, AUDIOCLAS_CONFIGFILE, tmpfile, descriptorFile)

	if mode == "-all":
		print "calculating descriptors..."
		print "\tcmd = %s" % cmd

		print "=========================== <AUDIOCLAS> ==========================="
		if call(cmd) != 0:
			print "calculating descriptors: FAILED"
			exitAudioclas(True)
		print "=========================== </AUDIOCLAS> ==========================="

	filename = os.path.splitext( filename )[0]

	if mode == "-all":
		cmd = '%s %s %s %s' % (AUDIOCLAS_EXECUTABLE_SPECTRAL_CENTROID, AUDIOCLAS_CONFIGFILE_SPECTRALCENTROID, tmpfile, colorFile)
		print "calculating spectral centroid for whole file..."
		print "\tcmd = %s" % cmd

		# write the spectral centroid in a file
		print "=========================== <AUDIOCLAS> ==========================="
		if call(cmd) != 0:
			print "calculating descriptors: FAILED"
			exitAudioclas(True)
		print "=========================== </AUDIOCLAS> ==========================="

		print "adding [128] to file"
		cmd = "(echo \'[128]\';cat %s) > %s;mv %s %s" % (colorFile,tmpfile2,tmpfile2,colorFile)
		print "cmd = %s" % cmd
		if os.system(cmd) != 0:
			print "adding [128] to file FAILED"
			exitAudioclas(True)
		#tmp = list(file(colorFile))
		#file(colorFile, "w").write("".join(["[128]\n"] + tmp))
		
		# spectralCentroid = '[128]\n%s' % (result_stream.read().strip())
		# spectralCentoidFile = open ( '%s_color.dat' % (filename), 'w' )
		# spectralCentoidFile.write ( spectralCentroid )
		# spectralCentoidFile.close()

	# create PNG file
	print "creating PNG preview, large"
	if mode == "-all":
		cmd = '%s -i %s -o %s -c %s' % (WAV2PNG, tmpfile, image, colorFile)
	else:
		cmd = '%s -i %s -o %s' % (WAV2PNG, tmpfile, image)
	print "\tcmd = %s" % cmd
        if call(cmd) != 0:
		print "PNG creation FAILED"
		exitAudioclas(True)

	print "creating PNG preview, small"
	if mode == "-all":
		cmd = '%s -i %s -o %s -c %s -w 80 -h 41' % (WAV2PNG, tmpfile, smallImage, colorFile)
	else:
		cmd = '%s -i %s -o %s -w 80 -h 41' % (WAV2PNG, tmpfile, smallImage)
	print "\tcmd = %s" % cmd
        if call(cmd) != 0:
		print "PNG creation FAILED"
		exitAudioclas(True)

	# all clear, exit nicely!
	exitAudioclas(False)

if sys.argv[1] == "-all":
	compute(sys.argv[1],sys.argv[2],sys.argv[3],sys.argv[4],sys.argv[5],sys.argv[6],sys.argv[7])
else:
	compute(sys.argv[1],sys.argv[2],sys.argv[3],sys.argv[4],sys.argv[5],"","")
