import logging
import json


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = '-' #request.META.get('REMOTE_ADDR')
    return ip


class SearchLogsFilter(logging.Filter):

    def filter(self, record):
        try:
            message = record.getMessage()
            json_part = message.split('Search (')[1][:-1]
            fields = json.loads(json_part)
            for key, value in fields.items():
                setattr(record, key, value)
        except IndexError:
            pass  # Message is not formatted for json parsing
        return True


class APILogsFilter(logging.Filter):

    def filter(self, record):
        message = record.getMessage().encode('utf8')
        try:
            (message, data, info) = message.split(' #!# ')
            record.api_resource = message
            for key, value in json.loads(info).items():
                setattr(record, key, value)
            for key, value in json.loads(data).items():
                setattr(record, key, value)
        except:
            pass
        return True
