# Create your views here.

def tags(request, multiple_tags=None):
    if multiple_tags:
        multiple_tags = multiple_tags.split('/')
    else:
        multiple_tags = []
    
    multiple_tags = filter(lambda x:x, multiple_tags)
    pass