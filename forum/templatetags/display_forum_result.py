'''
Created on Jul 1, 2011

@author: stelios
'''
from __future__ import absolute_import
from django import template

register = template.Library()

# TODO: do we need takes_context???
@register.inclusion_tag('forum/display_forum_result.html', takes_context=True)
def display_forum_result(context, post, highlight):
    results = []
    for thd in post:
        # highlight is dict, so not ordered. below we much results to highlighted results
        # TODO: find an efficient way to do this... maybe try except keyerror will be faster
        posts = []
        first_doc = thd['doclist']['docs']
        for p in first_doc:
            # highlighted result
            if str(p['id']) in highlight:
                posts.append({'post_id': p['id'],
                             'post_body': highlight[str(p['id'])]['post_body'][0],
                             'post_info': ' - '.join(['Post by: ' + p['post_author'],
                                                      'Date: ' + str(p['post_created'])])})
            else:
                posts.append({'post_id': p['id'],
                             'post_body': p['post_body'],
                             'post_info': ' - '.join(['Post by: ' + p['post_author'],
                                                      'Date: ' + str(p['post_created'])])})

        results.append({
                        'thread_id': first_doc[0]['thread_id'],
                        'thread_title': first_doc[0]['thread_title'],
                        'forum_name': first_doc[0]['forum_name'],
                        'forum_name_slug': first_doc[0]['forum_name_slug'],
                        'post_id': first_doc[0]['id'],
                        'posts': posts,
                        'thread_info': ' - '.join(['Forum: ' + first_doc[0]['forum_name'],
                                                   'Thread by: ' + first_doc[0]['thread_author'],
                                                   'Posts: ' + str(first_doc[0]['num_posts']),
                                                   'Date: ' + str(first_doc[0]['thread_created'])]),
                        })

    return { 'results': results }
