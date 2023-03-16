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
import argparse

from utils.audioprocessing.processing import create_wave_images, AudioProcessingException
import sys


def progress_callback(position, width):
    percentage = old_div((position*100),width)
    if position % (old_div(width, 10)) == 0:
        sys.stdout.write(str(percentage) + "% ")
        sys.stdout.flush()


def main(args):
    # process all files so the user can use wildcards like *.wav
    for input_file in args.files:

        output_file_w = input_file + "_w.png"
        output_file_s = input_file + "_s.jpg"

        this_args = (input_file, output_file_w, output_file_s, args.width, args.height, args.fft_size,
                     progress_callback, args.color_scheme)

        print(f"processing file {input_file}:\n\t", end="")

        if not args.profile:
            try:
                create_wave_images(*this_args)
            except AudioProcessingException as e:
                print(f"Error running wav2png: {e}")
        else:
            from hotshot import stats
            import hotshot

            prof = hotshot.Profile("stats")
            prof.runcall(create_wave_images, *this_args)
            prof.close()

            print("\n---------- profiling information ----------\n")
            s = stats.load("stats")
            s.strip_dirs()
            s.sort_stats("time")
            s.print_stats(30)
        print("")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("files", help="files to process", nargs="+")
    parser.add_argument("-w", "--width", type=int, default=500, dest="width",
                        help="image width in pixels")
    parser.add_argument("-H", "--height", type=int, default=171, dest="height",
                        help="image height in pixels")
    parser.add_argument("-f", "--fft", type=int, default=2048, dest="fft_size",
                        help="fft size, power of 2 for increased performance")
    parser.add_argument("-c", "--color_scheme", type=str, default='Freesound2', dest="color_scheme",
                        help="name of the color scheme to use (one of: 'Freesound2' (default), 'FreesoundBeastWhoosh', "
                             "'Cyberpunk', 'Rainforest')")
    parser.add_argument("-p", "--profile", action="store_true",
                        help="run profiler and output profiling information")

    args = parser.parse_args()
    main(args)
