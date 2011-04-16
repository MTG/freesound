from django.template import Library
import datetime, time
from django.template.defaultfilters import stringfilter

register = Library()

@register.filter
def tuple_to_time(t):
    return datetime.datetime(*t[0:6]) + datetime.timedelta(seconds=time.timezone)


@register.filter(name='truncate_string')
@stringfilter
def truncate_string(value, length):
    if len(value) > length:
        return value[:length-3] + u"..."
    else:
        return value

@register.filter
def duration(value):
    duration_minutes = int(value/60)
    duration_seconds = int(value) % 60
    duration_miliseconds = int((value - int(value)) * 1000)
    return "%02d:%02d:%03d" % (duration_minutes, duration_seconds, duration_miliseconds)

@register.filter
def in_list(value,arg):
    return value in arg