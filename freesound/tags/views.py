# Create your views here.

def tags(request, multiple_tags=None):
    if multiple_tags:
        multiple_tags = multiple_tags.split('/')
    else:
        multiple_tags = []
    
    pass