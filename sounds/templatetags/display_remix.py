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

#avoid namespace clash with 'tags' templatetag
from django import template
import json


register = template.Library()
@register.inclusion_tag('sounds/display_remix.html', takes_context=True)

# TODO: ***just a reminder***
#       there is probably a more efficient way to prepare the data
#       CHECK ===> documentation for v.Layout.Network.Link #sourceNode
#
# FIXME: pagination doesn't work with this, we're missing the source....
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
                                    'eccentricity' : __calculateEccentricity(len(sounds)) 
                                    }) }    
 
# Calculate eccentricity so the arcs don't get clipped
# N.B. this is not the canonical way to calculate eccentricity but protovis uses this formula  
def __calculateEccentricity(sounds_length):
    eccentricity = 0
    if sounds_length > 3:
        a = (sounds_length-2) * 80
        b = 200
        eccentricity = (1 - b/a) * (1 - b/a)
    
    return eccentricity
