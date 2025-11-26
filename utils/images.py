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
from PIL import Image, ImageOps
from PIL.Image import Resampling


def extract_square(input_filename, output_filename, size: int):
    """Resize and crop image to square of size `size`.

    If the image is smaller than `size` in both dimensions, it is padded with white.
    If the image is smaller than `size` in only one dimension,
        it is resized to fit the largest dimension and then padded with white.
    Else, it is resized to fit the largest dimension and then cropped to square.

    See https://pillow.readthedocs.io/en/stable/handbook/tutorial.html#relative-resizing
    """
    im = Image.open(input_filename)

    if im.mode not in ("L", "RGB"):
        im = im.convert("RGB")

    if im.size[0] < size and im.size[1] < size:
        im = ImageOps.pad(im, (size, size), method=Resampling.LANCZOS, color="#fff")
    elif (im.size[0] < size < im.size[1]) or (im.size[0] > size > im.size[1]):
        reduced_size = (
            im.size[0] if im.size[0] < size else size,
            im.size[1] if im.size[1] < size else size,
        )
        im = im.resize(reduced_size, resample=Resampling.LANCZOS)
        im = ImageOps.pad(im, (size, size), method=Resampling.LANCZOS, color="#fff")
    else:
        im = ImageOps.fit(im, (size, size), method=Resampling.LANCZOS)
    im.save(output_filename)


if __name__ == "__main__":
    import sys
    import os.path

    input_filename = sys.argv[1]
    size = int(sys.argv[2])
    path, ext = os.path.splitext(input_filename)
    output_filename = path + "_t" + ext
    extract_square(input_filename, output_filename, size)
