from django.core.management.base import BaseCommand
from forum.models import Thread
from forum.models import Post


class Command(BaseCommand):
    args = ''
    help = 'Fill first_post field in every Thread object'

    def handle(self, *args, **options):
        thread_qs = Thread.objects.all()
        for thread in thread_qs:
            first_post = thread.post_set.all()[0]
            thread.first_post = first_post
            thread.save()
