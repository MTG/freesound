from django.core.management.base import BaseCommand
from similarity.client import Similarity


class Command(BaseCommand):
    args = ''
    help = 'Save current similarity index'

    def handle(self, *args, **options):
        Similarity.save()