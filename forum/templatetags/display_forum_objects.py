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


from django import template

register = template.Library()


@register.inclusion_tag("forum/display_forum.html", takes_context=True)
def display_forum(context, forum):
    """This templatetag is used to display a forum in a list of forums. It prepares some variables that are then passed
    to the display_forum.html template to show forum information.

    Args:
        context (django.template.Context): an object with contextual information for rendering a template. This
          argument is automatically added by Django when calling the templatetag inside a template.
        forum (Forum): Forum object to display. For optimized database queries, the Forum object should come with
          .select_related('last_post', 'last_post__author', 'last_post__author__profile', 'last_post__thread').

    Returns:
        dict: dictionary with the variables needed for rendering the forum with the display_forum.html template

    """
    return {"forum": forum, "request": context["request"]}


@register.inclusion_tag("forum/display_thread.html", takes_context=True)
def display_thread(context, thread):
    """This templatetag is used to display a thread in a list of threads. It prepares some variables that are then
    passed to the display_thread.html template to show thread information.

    Args:
        context (django.template.Context): an object with contextual information for rendering a template. This
          argument is automatically added by Django when calling the templatetag inside a template.
        thread (Thread): Thread object to display. For optimized database queries, the Thread object should come with
          .select_related('last_post', 'last_post__author', 'last_post__author__profile', 'author', 'author__profile',
          'first_post', 'forum').

    Returns:
        dict: dictionary with the variables needed for rendering the thread with the display_thread.html template

    """
    return {"thread": thread, "request": context["request"]}


@register.inclusion_tag("forum/display_post.html", takes_context=True)
def display_post(
    context,
    post,
    forloop_counter=0,
    post_number_offset=0,
    show_post_location=False,
    show_action_icons=True,
    show_report_actions=True,
    results_highlighted=None,
    show_moderator_info=False,
):
    """This templatetag is used to display a post in a list of posts. It prepares some variables that are then
    passed to the display_post.html template to show post information.

    Args:
        context (django.template.Context): an object with contextual information for rendering a template. This
          argument is automatically added by Django when calling the templatetag inside a template.
        post (Post): Post object to display. For optimized database queries, the Post object should come with
          .select_related('thread', 'thread__forum', 'author', 'author__profile').
        forloop_counter (int): current count of the forloop calling the templatetag (user fo showing post number)
        post_number_offset (int): current count page offset of the forloop (user fo showing post number)
        show_post_location (bool): show Forum and Thread name of the post (used for forum search results)
        show_action_icons (bool): show quote/edit/delete action buttons and post number
        show_report_actions (bool): show links to admin pages for post/thread and for reporting post as spam
        results_highlighted (dict): dictionary with highlighted contents of all posts in the current search results
          page (with post IDs as keys of the dictionary). This is returned by the search engine.
        show_moderator_info (bool): show additional information about the post author for moderator purposes

    Returns:
        dict: dictionary with the variables needed for rendering the post with the display_post.html template

    """
    if results_highlighted is not None and str(post.id) in results_highlighted:
        try:
            highlighted_content = results_highlighted[str(post.id)]["post_body"][0]
        except KeyError:
            highlighted_content = False
    else:
        highlighted_content = False
    return {
        "post": post,
        "highlighted_content": highlighted_content,
        "post_number": forloop_counter + post_number_offset,
        "show_post_location": show_post_location,
        "show_action_icons": show_action_icons,
        "show_report_actions": show_report_actions,
        "show_moderator_info": show_moderator_info,
        "perms": context["perms"],
        "request": context["request"],
    }
