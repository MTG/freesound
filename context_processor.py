from django.conf import settings

def context_extra(request):
    return {'media_url': settings.MEDIA_URL,
            'request': request,
            'GOOGLE_API_KEY': settings.GOOGLE_API_KEY }
