import json
import pickle

from django.contrib.sessions.serializers import JSONSerializer


class TransitionalPickleSerializer(JSONSerializer):
    """Write JSON while retaining support for existing pickled sessions.

    Allows us to incrementally update active sessions.
    """

    def loads(self, data):
        try:
            return super().loads(data)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return pickle.loads(data)  # noqa: S301 - compatibility with signed legacy sessions
