import sys
import urllib.request, urllib.parse, urllib.error

sys.path.append("../../apiv2")
from examples import examples

base_url = 'https://freesound.org/'


def get_formatted_examples_for_view(view_name):
    try:
        data = examples[view_name]
    except:
        print(f'Could not find examples for view {view_name}')
        return ''

    output = ''
    for description, elements in data:
        output += f'\n\n{description}:\n\n'
        output += '::\n\n'
        for element in elements:
            if element[0:5] == 'apiv2':
                output += '  {}{}\n'.format(base_url, urllib.parse.quote(element, safe='?/=&",:()'))
                #output += '  curl -H "Authorization: Token {{token}}" \'%s%s\'\n' % (base_url, element)
            else:
                output += f"  {element % base_url[:-1].replace('http:', 'https:')}\n"

    return output


with open('source/resources.rst') as f:
    newlines = []
    for line in f.readlines():
        if '{{examples_' in line:
            name = line.split('{{')[1].split('}}')[0].split('_')[1]
            examples_string = get_formatted_examples_for_view(name)
            for example_line in examples_string.split('\n'):
                newlines.append(example_line + '\n')
        else:
            newlines.append(line)

with open('source/resources_apiv2.rst', 'w') as f:
    for line in newlines:
        f.write(line)
