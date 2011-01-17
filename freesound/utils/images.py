from PIL import Image

class ImageProcessingError(Exception):
    pass

def extract_square(input_filename, output_filename, size):
    im = Image.open(input_filename)
    
    if im.size[0] < size or im.size[1] < size:
        #raise ImageProcessingError, "image too small"
        #fill out to exactly maxSize (square image)          
        background = Image.new("RGBA", (size,size), (255, 255, 255, 0)) # use white for empty space  
        background.paste(im, ((size - im.size[0]) / 2, (size - im.size[1]) / 2))  
        background.save(output_filename)

    if im.size[0] > im.size[1]:
        # --------
        # |      |
        # --------
        box = (im.size[0]-im.size[1])/2, 0, im.size[0] - (im.size[0]-im.size[1])/2, im.size[1]
    else: 
        # ____
        # |  |
        # |  |
        # |__|
        box = 0, (im.size[1]-im.size[0])/2, im.size[0], im.size[1] - (im.size[1]-im.size[0])/2 
    
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