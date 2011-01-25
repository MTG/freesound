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
            ratio = im.size[1] / im.size[0]
            im = im.resize((size / ratio, size), Image.ANTIALIAS)            
        else: 
            ratio = im.size[0] / im.size[1] 
            im = im.resize((size,size / ratio), Image.ANTIALIAS)
        #fill out          
        background = Image.new("RGBA", (size,size), (255, 255, 255, 0)) # use white for empty space  
        background.paste(im, ((size - im.size[0]) / 2, (size - im.size[1]) / 2))  
        background.save(output_filename)
        return
        
    #if one side of the image is smaller and one is bigger
    elif im.size[0] > size and im.size[1] < size:
        ratio = im.size[0] / im.size[1]
        im = im.resize((size * ratio,size), Image.ANTIALIAS)  
                     
    elif im.size[0] < size and im.size[1] > size:  
        ratio = im.size[1] / im.size[0]
        im = im.resize((size, size * ratio), Image.ANTIALIAS)
           
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