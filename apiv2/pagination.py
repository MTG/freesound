from rest_framework import pagination
from django.conf import settings


class CustomPagination(pagination.PageNumberPagination):
    page_size = settings.APIV2["PAGE_SIZE"]
    page_size_query_param = settings.APIV2["PAGE_SIZE_QUERY_PARAM"]
    max_page_size = settings.APIV2["MAX_PAGE_SIZE"]
