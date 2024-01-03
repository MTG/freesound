'''
Created on Jul 1, 2011

@author: stelios
'''
from django import template

register = template.Library()


# TODO: do we need takes_context???
@register.inclusion_tag('forum/display_forum_result.html', takes_context=True)
def display_forum_search_results(context, results_docs, highlight):
    results = []
    for thd in results_docs:
        # highlight is dict, so not ordered. below we much results to highlighted results
        # TODO: find an efficient way to do this... maybe try except keyerror will be faster
        posts = []
        first_docs = thd['group_docs']
        for p in first_docs:
            # highlighted result
            if str(p['id']) in highlight:
                posts.append({
                    'post_id': p['id'],
                    'post_body': highlight[str(p['id'])]['post_body'][0],
                    'post_info': ' - '.join(['Post by: ' + p['post_author'], 'Date: ' + str(p['post_created'])])
                })
            else:
                posts.append({
                    'post_id': p['id'],
                    'post_body': p['post_body'],
                    'post_info': ' - '.join(['Post by: ' + p['post_author'], 'Date: ' + str(p['post_created'])])
                })

        results.append({
            'thread_id':
                first_docs[0]['thread_id'],
            'thread_title':
                first_docs[0]['thread_title'],
            'forum_name':
                first_docs[0]['forum_name'],
            'forum_name_slug':
                first_docs[0]['forum_name_slug'],
            'post_id':
                first_docs[0]['id'],
            'posts':
                posts,
            'thread_info':
                ' - '.join([
                    'Forum: ' + first_docs[0]['forum_name'], 'Thread by: ' + first_docs[0]['thread_author'],
                    'Posts: ' + str(first_docs[0]['num_posts']), 'Date: ' + str(first_docs[0]['thread_created'])
                ]),
        })

    return {'results': results}
