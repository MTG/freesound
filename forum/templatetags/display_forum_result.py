'''
Created on Jul 1, 2011

@author: stelios
'''
from __future__ import absolute_import
from django import template

register = template.Library()

@register.inclusion_tag('forum/display_forum_result.html', takes_context=True)
def display_forum_result(context, thread):
    print "**************** forum result ********************"
    post = thread['post'][0] if thread['post'] else False  
    # print post
    post = __get_post_body(post)
    return {
            'id': thread['id'],
            'thread_name': thread['thread_name'],
            'forum_name': thread['forum_name'],
            'post': post,
            'thread_info': ' - '.join([thread['username'], str(thread['num_posts']), str(thread['created'])]),
            }

def __get_post_body(post):
    ret = post.split(',', 3)
    ret = ret[3].rsplit('datetime.datetime')
    return ret[0]