import tempfile

from django.test import TestCase

from utils.filesystem import md5file


class Test(TestCase):

    def test_md5file(self):
        with tempfile.NamedTemporaryFile() as tmp_fh:
            tmp_fh.write(b"test_content\n")
            tmp_fh.flush()
            self.assertEqual("87978e0dfadc2f75cafc0d21600eaa55", md5file(tmp_fh.name))
