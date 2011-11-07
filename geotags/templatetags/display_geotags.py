'''
Created on Nov 3, 2011

@author: groma
'''
from django import template

register = template.Library()

@register.inclusion_tag('geotags/display_geotags.html', takes_context=True)
def display_geotags(context, url = "/geotags/geotags_box_json/", width = 900, height = 600, clusters = "on", center_lat = None, center_lon = None, zoom = None):
    if center_lat and center_lon and zoom:
        borders = "defined"
    else:
        borders = "automatic"
    
    return {"url":url, "media_url": context['media_url'], "m_width":width, "m_height":height, "clusters":clusters, "center_lat":center_lat, "center_lon":center_lon, "zoom":zoom, "borders":borders}