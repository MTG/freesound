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
from PIL import Image

class ImageProcessingError(Exception):
    pass

def extract_square(input_filename, output_filename, size):
    im = Image.open(input_filename)

    if im.mode not in ('L', 'RGB'):
        im = im.convert('RGB')

    #fill out and resize the image
    if im.size[0] < size and im.size[1] < size:
        if im.size[0] < im.size[1]:
            ratio = old_div(im.size[1], im.size[0])
            im = im.resize((old_div(size, ratio), size), Image.ANTIALIAS)            
        else: 
            ratio = old_div(im.size[0], im.size[1]) 
            im = im.resize((size,old_div(size, ratio)), Image.ANTIALIAS)
        #fill out          
        background = Image.new("RGB", (size,size), (255, 255, 255)) # use white for empty space
        background.paste(im, (old_div((size - im.size[0]), 2), old_div((size - im.size[1]), 2)))  
        background.save(output_filename)
        return
        
    #if one side of the image is smaller and one is bigger
    elif im.size[0] > size and im.size[1] < size:
        ratio = old_div(im.size[0], im.size[1])
        im = im.resize((size * ratio,size), Image.ANTIALIAS)  
                     
    elif im.size[0] < size and im.size[1] > size:  
        ratio = old_div(im.size[1], im.size[0])
        im = im.resize((size, size * ratio), Image.ANTIALIAS)
           
    if im.size[0] > im.size[1]:
        # --------
        # |      |
        # --------
        box = old_div((im.size[0]-im.size[1]),2), 0, im.size[0] - old_div((im.size[0]-im.size[1]),2), im.size[1]
    else: 
        # ____
        # |  |
        # |  |
        # |__|
        box = 0, old_div((im.size[1]-im.size[0]),2), im.size[0], im.size[1] - old_div((im.size[1]-im.size[0]),2) 
    
    im = im.crop(box)
    im.thumbnail((size, size), Image.ANTIALIAS)
    im.save(output_filename)

if __name__ == "__main__":
    import sys, os.path
    input_filename = sys.argv[1]
    size = int(sys.argv[2])
    path, ext = os.path.splitext(input_filename)
    output_filename = path + "_t" + ext 
    extract_square(input_filename, output_filename, size)