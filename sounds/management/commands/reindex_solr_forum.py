from django.core.management.base import BaseCommand
from forum.models import Post
from utils.search.search_forum import add_all_posts_to_solr

class Command(BaseCommand):
    args = ''
    help = 'Take all posts and send them to Solr'

    def handle(self, *args, **options):
        post_qs = Post.objects.select_related("forum", "thread", "user")
        add_all_posts_to_solr(post_qs)