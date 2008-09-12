import unittest, re
from BeautifulSoup import BeautifulSoup, Comment

def shout_percentage(string):
    if len(string):
        return sum(1 for s in string if s != s.lower() or s == "!") / float(len(string))
    else:
        return 0

def is_shouting(string):
    """
    >>> is_shouting('')
    False
    >>> is_shouting('HELLO THIS IS SHOUTING!!!')
    True
    >>> is_shouting('This is a phrase WITH SONE emphasis!!')
    False
    >>> is_shouting('This is a regular phrase.')
    False
    """
    return shout_percentage(string) > 0.6


# returns if the string ends with any of the endinggs
def endswithone(string, endings):
    reduce(lambda a,b: a or string.endswith(b), endings, False)

# returns if the string starts with any of the starts
def startswithone(string, starts):
    reduce(lambda a,b: a or string.startswith(b), starts, False)


url_regex = re.compile("(http://[^ ]+)", re.IGNORECASE)

def replace_element_by_children(soup, element):
    """
    replace an element in the DOM with it's child nodes
    """
    parent = element.parent
        
    if not parent:
        parent = soup
    
    # afterwards we need to insert the children where the parent used to be!
    position_in_parent = 0
    for c in parent.contents:
        if c == element:
            break
        else:
            position_in_parent += 1
    
    # in reverse order, insert the child elements in their place.
    for el in element.contents[::-1]:
        parent.insert(position_in_parent, el)

    # delete the element
    element.extract()


def clean_html(input):
    """
    >>> clean_html('a b c d')
    'a b c d'
    >>> clean_html('<a href="http://www.google.com" rel="squeek">google</a>')
    '<a href="http://www.google.com" rel="nofollow">google</a>'
    >>> clean_html('<a href="http://www.google.com">google</a>')
    '<a href="http://www.google.com" rel="nofollow">google</a>'
    >>> clean_html('<h1>this should return the <strong>substring</strong> just <b>fine</b></h1>')
    'this should return the <strong>substring</strong> just <b>fine</b>'
    >>> clean_html('<table><tr><td>amazing</td><td>grace</td></tr></table>')
    'amazinggrace'
    >>> clean_html('<a href="javascript:void(0)">click me</a>')
    'click me'
    >>> clean_html('<p class="hello">click me</p>')
    '<p>click me</p>'
    >>> clean_html('<a></a>')
    ''
    >>> clean_html('<p>         </p>')
    '<p> </p>'
    >>> clean_html('<a>hello</a>')
    'hello'
    >>> clean_html('<p class="hello" id="1">a<br/>b<br/></a>')
    '<p>a<br />b<br /></p>'
    >>> clean_html('<p></p>')
    '<p></p>'
    >>> clean_html('<a rel="nofollow" href="http://www.google.com"><strong>http://www.google.com</strong></a>')
    '<a href="http://www.google.com" rel="nofollow"><strong>http://www.google.com</strong></a>'
    >>> clean_html('http://www.google.com <a href="">http://www.google.com</a>')
    '<a href="http://www.google.com" rel="nofollow">http://www.google.com</a> <a href="http://www.google.com" rel="nofollow">http://www.google.com</a>'
    >>> clean_html('<ul><p id=5><a href="123">123</a>hello<tr></tr><strong class=156>there http://www</strong></p></ul>')
    '<ul><p>123hello<strong>there <a href="http://www" rel="nofollow">http://www</a></strong></p></ul>'
    """
    
    delete_tags = ["script", "style", "head"]
    ok_tags = ["a", "img", "strong", "b", "em", "i", "u", "p", "br", "ul", "li"]
    ok_attributes = {"a": ["href"], "img": ["src", "alt", "title"]}
    # all other tags: replace with the content of the tag
    
    soup = BeautifulSoup(input)
    
    # delete all comments
    [comment.extract() for comment in soup.findAll(text=lambda text:isinstance(text, Comment))]

    for element in soup.findAll():
        if element.name in delete_tags:
            element.extract()
            continue
        
        if element.name not in ok_tags:
            replace_element_by_children(soup, element)
            continue
            
        try:
            if element.name in ok_attributes.keys():
                # delete all attributes we don't want
                for (attr_name, attr_value) in element.attrs:
                    if attr_name not in ok_attributes[element.name]:
                        del element[attr_name]

                if element.name == "a":
                    if "href" not in dict(element.attrs) or not element["href"].startswith("http://"):
                        replace_element_by_children(soup, element)
                    else:
                        element["rel"] = "nofollow"
                elif element.name == "img":
                    if "src" not in dict(element.attrs) or not element["src"].startswith("http://"):
                        replace_element_by_children(soup, element)
            else:
                # these should not have any attributes
                element.attrs = []
        except AttributeError:
            if element.name in ok_attributes.keys():
                replace_element_by_children(soup, element)

    for text in soup.findAll(text=url_regex):
        if not text.findParents('a'):
            text.replaceWith(url_regex.sub(r'<a href="\1" rel="nofollow">\1</a>', text))
    
    return str(soup)


def _test():
    import doctest
    doctest.testmod()

if __name__ == "__main__":
    _test()