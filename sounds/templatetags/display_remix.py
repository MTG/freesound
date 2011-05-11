'''
Created on May 6, 2011

@author: stelios
'''
from __future__ import absolute_import
#avoid namespace clash with 'tags' templatetag
from django import template
import json

register = template.Library()
@register.inclusion_tag('sounds/display_remix.html', takes_context=True)

# FIXME: the links are wrong!!!
# how can I know which is source and which target, doesn't come in the data per se
# I can create the nodes, then see which node has id=sound.id
# but this is a list of dictionaries... 
def display_remix(context, sound, objectlist):
    
    nodes = []
    links = []
    remix1 = {'nodeName':sound.original_filename, 'group':1, 'id':sound.id}
    # nodes.append(remix1)
    for idx,val in enumerate(objectlist):
        nodes.append({'nodeName':val.original_filename, 'group':1, 'id':val.id, 'pos':idx})
        if val.sources:
            print(val.sources.all())
        if val.remixes:
            print(val.remixes.all())
        # links.append({'source':0, 'target':0, 'value':1})
        
    # maybe can do a second pass here... in the queryset object and make the links
                
         
            
    return  { 'data' :  json.dumps({'nodes' : nodes, 'links' : links, 'username' : sound.user.username}) }
    
