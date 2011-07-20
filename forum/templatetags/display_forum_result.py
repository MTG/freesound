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
        post = []
        first_doc = thd['doclist']['docs'][0]
        # highlighted result
        if str(thd['doclist']['docs'][0]['id']) in highlight:
            post.append({'post_id': first_doc['id'],
                         'post_body': highlight[str(first_doc['id'])]['post_body'][0],
                         'post_info': ' - '.join(['Post by: ' + first_doc['post_author'],
                                                  'Date: ' + str(first_doc['post_created'])])})
        else:
            post.append({'post_id': thd['doclist']['docs'][0]['id'], 
                         'post_body': thd['doclist']['docs'][0]['post_body'],
                         'post_info': ' - '.join(['Post by: ' + first_doc['post_author'],
                                                  'Date: ' + str(first_doc['post_created'])])})
        
        # up to 3 posts per group can be returned    
        if thd['doclist']['numFound'] > 1:
            for idx,val in enumerate(thd['doclist']['docs']):
                if idx > 0:
                    post.append({'post_id': val['id'], 
                                 'post_body': val['post_body'],
                                 'post_info': ' - '.join(['Post by: ' + val['post_author'],
                                                          'Date: ' + str(val['post_created'])])})

        results.append({
                        'thread_id': first_doc['thread_id'],
                        'thread_title': first_doc['thread_title'],
                        'forum_name': first_doc['forum_name'],
                        'forum_name_slug': first_doc['forum_name_slug'],
                        'post_id': first_doc['id'],
                        'post': post,
                        'thread_info': ' - '.join(['Thread by: ' + first_doc['thread_author'], 
                                                   'Posts: ' + str(first_doc['num_posts']), 
                                                   'Date: ' + str(first_doc['thread_created'])]),
                        }) 
    
    return { 'results': results }