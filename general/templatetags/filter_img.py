from django import template
from bs4 import BeautifulSoup, Tag
from os.path import basename, splitext

register = template.Library()


@register.filter(is_safe=True)
def replace_img(string):
    if not "<img" in string or not "http:" in string:
        return string

    soup = BeautifulSoup(string)
    for img in soup.find_all('img'):
        if not img['src'].lower().startswith("https"):
            a = soup.new_tag("a", href=img['src'])
            a.string = img['src']
            img.replace_with(a)
    return str(soup)
