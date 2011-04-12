from django import template

register = template.Library()

@register.inclusion_tag('sounds/license_form.html', takes_context=True)
def display_license_form(context, form):
    license_ids = dict([(str(x.name).replace(' ', '_'), str(x.id)) for x in form.fields['license'].choices.queryset])
    #print form.fields['license'].choices.choice()
    return {'form': form, 'license_ids': license_ids}