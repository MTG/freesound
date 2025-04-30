from django.urls.converters import StringConverter

class MultipleTagsConverter(StringConverter):
    regex = r'[\w/-]+'