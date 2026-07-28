import tempfile

from django.core.management import call_command
from django.test import TestCase, override_settings


class CreateDataPackCommandTests(TestCase):
    fixtures = ["licenses", "sounds"]

    def test_limit_zero_runs_with_single_query(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with override_settings(DATA_PACKS_PATH=temp_dir):
                # In sounds fixture, max sound ID is less than 1000, therefore the command will only need one chunk
                # The command should run with 2 queries:
                # 1. Get all sound IDs
                # 2. Get the sound objects for those IDs
                with self.assertNumQueries(2):
                    call_command("create_data_pack")
