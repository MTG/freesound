"""Custom management command to set/clear announcement_cache for front page announcements banner.

The announcement banner is a simple HTML snippet cached in the Django cache. It is formed by a title and a text
that are passed as arguments to the command. The command can be used to set the cache, clear it, or show the current
value of the cache.

Example usage:
    python manage.py announcement_banner set "New feature!" "Now you can do this and that. <a href='/forum'>Learn more</a>"
    python manage.py announcement_banner set "" "This banner will have no title. Now you can do this and that. <a href='/forum'>Learn more</a>"
    python manage.py announcement_banner set "" "short text with a 60 seconds timeout" --timeout 60
    python manage.py announcement_banner clear
    python manage.py announcement_banner show

"""
from django.conf import settings
from django.core.cache import cache
from django.core.management.base import BaseCommand
from django.template.loader import render_to_string


class Command(BaseCommand):
    help = 'Set/clear "announcement_cache" for front page announcements banner'

    def add_arguments(self, parser):
        subparsers = parser.add_subparsers(title="action", dest="action", required=True)
        set_parser = subparsers.add_parser("set", help="Set the announcement_cache")
        set_parser.set_defaults(action="set")
        set_parser.add_argument("title", type=str, help="Title of the announcement")
        set_parser.add_argument("text", type=str, help="Text of the announcement")
        set_parser.add_argument("--timeout", type=int, help="Timeout for the cache in seconds")

        clear_parser = subparsers.add_parser("clear", help="Clear the announcement_cache")
        clear_parser.set_defaults(action="clear")

        show_parser = subparsers.add_parser("show", help="Show the current value of the announcement_cache")
        show_parser.set_defaults(action="show")

    def handle(self, *args, **kwargs):
        action = kwargs["action"]

        if action == "set":
            title = kwargs["title"]
            text = kwargs["text"]
            timeout = kwargs.get("timeout")
            value = render_to_string("molecules/announcement_banner.html", {"title": title, "text": text})
            cache.set(settings.ANNOUNCEMENT_CACHE_KEY, value, timeout)
            self.stdout.write(self.style.SUCCESS("Successfully set announcement_cache"))
        elif action == "clear":
            cache.delete(settings.ANNOUNCEMENT_CACHE_KEY)
            self.stdout.write(self.style.SUCCESS("Successfully cleared announcement_cache"))
        elif action == "show":
            current_value = cache.get(settings.ANNOUNCEMENT_CACHE_KEY, "<<Cache is empty>>")
            self.stdout.write(self.style.SUCCESS("Current value of announcement_cache:"))
            self.stdout.write(current_value)
        else:
            self.stdout.write(self.style.ERROR('Invalid action. Use "set" or "clear".'))
