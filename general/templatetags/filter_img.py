from bs4 import BeautifulSoup
from django import template

register = template.Library()


@register.filter(is_safe=True)
def replace_img(string):
    if not string or not "<img" in string or "http:" not in string:
        return string

    soup = BeautifulSoup(string, "html.parser")
    for img in soup.find_all("img"):
        if img.has_attr("src") and not img["src"].lower().startswith("https"):
            a = soup.new_tag("a", href=img["src"])
            a.string = img["src"]
            img.replace_with(a)
    return str(soup)
