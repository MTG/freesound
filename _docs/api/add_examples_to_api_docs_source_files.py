import sys
sys.path.append("../../apiv2")
from examples import examples


def get_formatted_examples_for_view(view_name):
    try:
        data = examples[view_name]
    except:
        print 'Could not find examples for view %s' % view_name
        return ''

    output = ''
    for description, elements in data:
        output += '\n\n%s\n\n' % description
        output += '::\n\n'
        for element in elements:
            output += '  curl %s\n' % element

    return output



with open('source/resources.rst', 'r') as f:
    newlines = []
    for line in f.readlines():
        if '{{examples_search}}' in line:
            examples_string = get_formatted_examples_for_view('Search')
            for example_line in examples_string.split('\n'):
                newlines.append(example_line + '\n')
        else:
            newlines.append(line)

with open('source/resources_apiv2.rst', 'w') as f:
    for line in newlines:
        f.write(line)