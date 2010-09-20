from django_extensions.management.jobs import HourlyJob
from sounds.models import Pack


class Job(HourlyJob):
    help = "Find packs that need refreshing and create them"

    def execute(self):
        for pack in Pack.objects.filter(is_dirty=True):
            pack.create_zip()