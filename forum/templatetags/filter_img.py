from django import template
from BeautifulSoup import BeautifulSoup, Tag
from os.path import basename, splitext

register = template.Library()


@register.filter(is_safe=True)
def replace_img(string):
    soup = BeautifulSoup(string)
    for img in soup.findAll('img'):
        if not img['src'].lower().startswith("https"):
            a = Tag(soup, "a")
            a['href'] = img['src']
            a.string = "(Unsecure image)"
            img.replaceWith(a)
    return str(soup)
