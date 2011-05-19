'''
Created on May 6, 2011

@author: stelios
'''
from __future__ import absolute_import, division
#avoid namespace clash with 'tags' templatetag
from django import template
import json
from random import randint

register = template.Library()
@register.inclusion_tag('sounds/display_remix.html', takes_context=True)

# TODO: ***just a reminder***
#       there is probably a more efficient way to prepare the data
#       CHECK ===> documentation for v.Layout.Network.Link #sourceNode
def display_remix(context, sound, sounds):
    
    nodes = []
    links = []
    tempList = []

    # get position in queryset related to ids
    # we need this to create the links between the nodes
    for idx,val in enumerate(sounds):
        tempList.append({'id': val.id, 'pos': idx})
            
    for idx,val in enumerate(sounds):
        nodes.append({
                      'nodeName':val.original_filename,
                      'group':1,
                      'id':val.id,
                      'username': val.user.username
                      })
        
        # since we go forward in time, if a sound has sources you can assign its sources
        # the target will always be the current object
        for src in val.sources.all():
            # we don't want the sources of the first item 
            # since that could give us the whole graph
            if idx > 0:
                links.append({
                              'source': str([t['pos'] for t in tempList if t['id']==src.id]).strip('[,]'),
                              'source_id': src.id, 
                              'target': idx,
                              'target_id': val.id,
                              'value': 1
                              })
            
            
    return  { 'data' :  json.dumps({
                                    'nodes' : nodes,
                                    'links' : links,
                                    'length': len(sounds),   # to calculate canvas height
                                    'color': '#F1D9FF',
                                    }) }    
    
