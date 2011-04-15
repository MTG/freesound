from django import template

register = template.Library()

@register.inclusion_tag('accounts/recursive_file.html')
def show_file(file_structure):
    return {'file': file_structure}