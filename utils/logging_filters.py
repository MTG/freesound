import logging
import json


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = '-' #request.META.get('REMOTE_ADDR')
    return ip


class GenericDataFilter(logging.Filter):
    """
    This filter expects a message of the form:
        XXX(YYY)
    Where XXX can be anything, YYY must be a serialized json object, and the message ends with )
    Assuming this format, the filter tries to separate the json part, unserialize it and add it as
    properties of the emessage so graylog can process them. If the parsing does not succeed, the 
    message is sent as is.
    """
    def filter(self, record):
        try:
            message = record.getMessage()
            json_part = message[message.find('(') + 1:-1]
            fields = json.loads(json_part)
            for key, value in fields.items():
                setattr(record, key, value)
        except (IndexError, ValueError, AttributeError):
            pass  # Message is not formatted for json parsing
        return True


class APILogsFilter(logging.Filter):

    def filter(self, record):
        message = record.getMessage().encode('utf8')
        try:
            (message, data, info) = message.split(' #!# ')
            if ':' in message:
                message = ' '.join([item.split(':')[0] for item in message.split(' ')])
            record.api_resource = message
            for key, value in json.loads(info).items():
                setattr(record, key, value)
            for key, value in json.loads(data).items():
                setattr(record, key, value)
        except:
            pass
        return True
