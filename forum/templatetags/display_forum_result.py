'''
Created on Jul 1, 2011

@author: stelios
'''
from __future__ import absolute_import
from django import template

register = template.Library()

@register.inclusion_tag('forum/display_forum_result.html', takes_context=True)
def display_forum_result(context, post, highlight):
    results = []
    for thd, hl in zip(post, highlight):
        print thd
        print highlight[hl]
        post = highlight[hl]['post_body']   
        results.append({
                        'thread_id': thd['doclist']['docs'][0]["thread_id"],
                        'thread_title': thd['doclist']['docs'][0]['thread_title'],
                        'forum_name': thd['doclist']['docs'][0]['forum_name'],
                        'forum_name_slug': thd['doclist']['docs'][0]['forum_name_slug'],
                        'post_id': thd['doclist']['docs'][0]["id"],
                        'post': post[0],
                        'thread_info': ' - '.join(['User: ' + thd['doclist']['docs'][0]['thread_author'], 
                                                   'Posts: ' + str(thd['doclist']['docs'][0]['num_posts']), 
                                                   'Date: ' + str(thd['doclist']['docs'][0]['thread_created'])]),
                        }) 
    
    return { 'results': results }