import unittest
from tags.models import FS1Tag, Tag

class FS1TagTestCase(unittest.TestCase):
    def setUp(self):
        self.horror = FS1Tag.objects.create(fs1_tag=928, tag=Tag.objects.get(name="horror"))
        self.close = FS1Tag.objects.create(fs1_tag=249, tag=Tag.objects.get(name="close"))

    def testMapTag(self):
        self.assertEqual(self.horror__tag, FS1Tag.objects.get(fs1_tag=928).tag)
        self.assertEqual(self.close__tag, FS1Tag.objects.get(fs1_tag=249).tag)
