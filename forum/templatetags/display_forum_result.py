'''
Created on Jul 1, 2011

@author: stelios
'''
from __future__ import absolute_import
from django import template

register = template.Library()

@register.inclusion_tag('forum/display_forum_result.html', takes_context=True)
def display_forum_result(context, thread, highlight):
    # TODO: refactor this uglyness...
    print "**************** forum result ********************"
    results = []
    for thd, hl in zip(thread, highlight):
        post = highlight[hl]['post'][0] if highlight[hl]['post'] else False   
        post = __get_post_body(post)
        results.append({
                        'id': thd['id'],
                        'thread_name': highlight[hl]['thread_name'][0],
                        'forum_name': thd['forum_name'],
                        'forum_name_slug': thd['forum_name_slug'],
                        'post': post,
                        'thread_info': ' - '.join(['User: ' + thd['username'], 
                                                   'Posts: ' + str(thd['num_posts']), 
                                                   'Date: ' + str(thd['created'])]),
                        }) 
    
    return { 'results': results }

def __get_post_body(post):
    ret = post.split(',', 3)
    ret = ret[3].rsplit('datetime.datetime')
    return ret[0]