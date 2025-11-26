#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "freesound.settings")

    if "--settings=freesound.test_settings" not in sys.argv:
        from django.conf import settings

        if settings.DEBUG:
            if (os.environ.get("RUN_MAIN") or os.environ.get("WERKZEUG_RUN_MAIN")) and not os.environ.get(
                "DISABLE_DEBUGPY"
            ):
                import debugpy

                debugpy.listen((settings.DEBUGGER_HOST, settings.DEBUGGER_PORT))
                print(f"Debugger ready and listening at http://{settings.DEBUGGER_HOST}:{settings.DEBUGGER_PORT}/")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)
