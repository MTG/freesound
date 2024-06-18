"""Custom management command to set/clear announcement_cache for front page announcements banner.

The announcement banner is a simple HTML snippet cached in the Django cache. It is formed by a title and a text
that are passed as arguments to the command. The command can be used to set the cache, clear it, or show the current
value of the cache.

Example usage:
    python manage.py announcement_cache set "New feature!" "Now you can do this and that. <a href='/forum'>Learn more</a>"
    python manage.py announcement_cache clear
    python manage.py announcement_cache show

"""
from django.core.cache import cache
from django.core.management.base import BaseCommand
from django.template.loader import render_to_string


class Command(BaseCommand):
    help = 'Set/clear "announcement_cache" for front page announcements banner'

    def add_arguments(self, parser):
        parser.add_argument("action", type=str, help="Indicates whether to set or clear the cache")
        parser.add_argument("title", type=str, nargs="?", help="Title of the announcement")
        parser.add_argument("text", type=str, nargs="?", help="Text of the announcement")

    def handle(self, *args, **kwargs):
        action = kwargs["action"]
        title = kwargs["title"]
        text = kwargs["text"]

        announcement_cache_key = "announcement_cache"
        if action == "set":
            one_day = 60 * 60 * 24
            value = render_to_string("molecules/announcement_banner.html", {"title": title, "text": text})
            cache.set(announcement_cache_key, value, one_day)
            self.stdout.write(self.style.SUCCESS("Successfully set announcement_cache"))
        elif action == "clear":
            cache.delete(announcement_cache_key)
            self.stdout.write(self.style.SUCCESS("Successfully cleared announcement_cache"))
        elif action == "show":
            current_value = cache.get(announcement_cache_key, "<<Cache is empty>>")
            self.stdout.write(self.style.SUCCESS("Current value of announcement_cache:"))
            self.stdout.write(current_value)
        else:
            self.stdout.write(self.style.ERROR('Invalid action. Use "set" or "clear".'))
