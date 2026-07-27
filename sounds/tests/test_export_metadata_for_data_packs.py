import tempfile

from django.core.management import call_command
from django.test import TestCase, override_settings


class ExportMetadataForDataPacksCommandTests(TestCase):
    fixtures = ["licenses", "sounds"]

    def test_limit_zero_runs_with_single_query(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with override_settings(DATA_PACKS_EXPORT_PATH=temp_dir):
                # In sounds fixture, max_id is less than 1000, therefore the command will only create one CSV file
                # The command should run with 3 queries:
                # 1. Get the max sound ID
                # 2. Get the sound IDs in the range 0-1000
                # 3. Get the sound objects for those IDs
                with self.assertNumQueries(3):
                    call_command("export_metadata_for_data_packs")
