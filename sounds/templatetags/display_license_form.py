from django import template

register = template.Library()

@register.inclusion_tag('sounds/license_form.html', takes_context=True)
def display_license_form(context, form):
    return {'form': form, "media_url": context['media_url']}