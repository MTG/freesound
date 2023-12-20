#
# Freesound is (c) MUSIC TECHNOLOGY GROUP, UNIVERSITAT POMPEU FABRA
#
# Freesound is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# Freesound is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# Authors:
#     See AUTHORS file.
#

from builtins import str
from builtins import range


def parse_filter(filter_string, layout_descriptor_names):
    ALLOWED_CONTENT_BASED_SEARCH_DESCRIPTORS = layout_descriptor_names

    operators = ['OR', 'AND', '(', ')']

    # Find ':'
    filter_struct = []

    min_pos = 0
    while filter_string.find(':', min_pos) != -1:
        current_pos = filter_string.find(':', min_pos)
        min_pos = current_pos + 1

        # Left part (feature name)
        previous_space_pos = filter_string.rfind(' ', 0, current_pos)
        feature_name = filter_string[previous_space_pos + 1:current_pos]
        if feature_name[0] != '.':
            feature_name = '.' + feature_name

        # Right part (value, range)
        if filter_string[current_pos + 1] == '[':
            next_space_pos = current_pos + 1
            for i in range(0, 3):
                next_space_pos = filter_string.find(' ', next_space_pos + 1)
            right_part = filter_string[current_pos + 2:next_space_pos]
            type_val = "RANGE"

        elif filter_string[current_pos + 1] == '"':
            next_quote_pos = filter_string.find('"', current_pos + 2)
            right_part = filter_string[current_pos + 1:next_quote_pos + 1]
            type_val = "STRING"
        else:
            next_space_pos = filter_string.find(' ', current_pos + 1)
            if next_space_pos == -1:
                next_space_pos = len(filter_string)
            right_part = filter_string[current_pos + 1:next_space_pos + 1]
            if not "," in right_part:
                type_val = "NUMBER"
            else:
                type_val = "ARRAY"

        for op in operators:
            feature_name = feature_name.replace(op, "")
            right_part = right_part.replace(op, "")

        # Check if the feature name is allowed (if is correct).
        # As filtering in multidimensional descriptors is indicated by (excample) feature.name.3 or feature.name.0, we
        # also check the existence of this feature name by removing the last number (and dot)
        if feature_name not in ALLOWED_CONTENT_BASED_SEARCH_DESCRIPTORS and feature_name.split(
                '[')[0] not in ALLOWED_CONTENT_BASED_SEARCH_DESCRIPTORS:
            return 'Filter error: At least one feature name does not match with any descirptor name in our database or the matched descriptor can not be used in a filter (' + str(
                feature_name
            ) + '). '

        filter_struct.append({
            'feature': feature_name,
            'type': type_val,
            'value': right_part,
            'delimiter_position': current_pos,
            'id': len(filter_struct) + 1
        })

    # Find OPERATORS clauses
    aux_ops = {}
    for op in operators:
        min_pos = 0
        while filter_string.find(op, min_pos) != -1:
            current_pos = filter_string.find(op, min_pos)
            min_pos = current_pos + 1
            aux_ops[current_pos] = op    #.append({'op':op,'pos':current_pos})
    keylist = sorted(aux_ops.keys())
    for key in keylist:
        op = aux_ops[key]
        current_pos = key

        # Insert OPERATOR clause in appropiate place of filter_struct
        for i, f in enumerate(filter_struct):
            if isinstance(f, dict):
                if f['delimiter_position'] > current_pos:
                    filter_struct.insert(i, op)
                    break
        if filter_struct[-1]['delimiter_position'] < current_pos:
            filter_struct.append(op)

    # Add AND operators by default (only where there are no other operators between two features)
    final_filter_struct = []
    for i in range(0, len(filter_struct)):
        if i < len(filter_struct) - 1:
            if isinstance(filter_struct[i], dict) and isinstance(filter_struct[i + 1], dict):
                final_filter_struct.append(filter_struct[i])
                final_filter_struct.append('AND')
            elif isinstance(filter_struct[i], dict) and filter_struct[i + 1] == "(":
                final_filter_struct.append(filter_struct[i])
                final_filter_struct.append('AND')
            elif filter_struct[i] == ")" and isinstance(filter_struct[i + 1], dict):
                final_filter_struct.append(filter_struct[i])
                final_filter_struct.append('AND')
            else:
                final_filter_struct.append(filter_struct[i])
        else:
            final_filter_struct.append(filter_struct[i])

    # Check good pairing of parenthesis
    if final_filter_struct.count("(") != final_filter_struct.count(")"):
        return "Bad filter syntax."

    # Change values for current types
    for f in final_filter_struct:
        if isinstance(f, dict):
            if f['type'] == 'NUMBER':
                f['value'] = float(f['value'])
            elif f['type'] == 'ARRAY':
                f['value'] = [float(x) for x in f['value'].split(',')]
            elif f['type'] == 'STRING':
                f['value'] = str(f['value'].replace('sharp', '#'))
            elif f['type'] == 'RANGE':
                min_str = f['value'][:f['value'].find("TO") - 1]
                if min_str != "*":
                    min_v = float(min_str)
                else:
                    min_v = None
                max_str = f['value'][f['value'].find("TO") + 3:].replace(']', '')
                if max_str != "*":
                    max_v = float(max_str)
                else:
                    max_v = None
                f['value'] = {'min': min_v, 'max': max_v}

    #print final_filter_struct
    return final_filter_struct


def prepend_value_label(f):
    if f['type'] == 'NUMBER' or f['type'] == 'RANGE' or f['type'] == 'ARRAY':
        return "value"
    else:
        return "label"


def parse_filter_list(filter_list, coeffs):

    filter = "WHERE"
    for f in filter_list:
        if not isinstance(f, dict):
            filter += f
        else:
            if f['type'] == 'NUMBER' or f['type'] == 'STRING' or f['type'] == 'ARRAY':

                if f['type'] == 'NUMBER':
                    if coeffs:
                        if '[' in f['feature']:
                            # if character [ is in feature name it means that is multidimensional filter
                            f_name = f['feature'].split('[')[0]
                            f_dimension = int(f['feature'].split('[')[1].split(']')[0])
                            norm_value = coeffs[f_name]['a'][f_dimension] * f['value'] + coeffs[f_name]['b'][f_dimension]
                        else:
                            norm_value = coeffs[f['feature']]['a'][0] * f['value'] + coeffs[f['feature']]['b'][0]
                    else:
                        norm_value = f['value']
                elif f['type'] == 'ARRAY':
                    if coeffs:
                        if '[' in f['feature']:
                            # if character [ is in feature name it means that is multidimensional filter
                            f_name = f['feature'].split('[')[0]
                            norm_value = []
                            for i in range(len(f['value'])):
                                norm_value.append(coeffs[f_name]['a'][i] * f['value'][i] + coeffs[f_name]['b'][i])
                        else:
                            norm_value = []
                            for i in range(len(f['value'])):
                                norm_value.append(
                                    coeffs[f['feature']]['a'][i] * f['value'][i] + coeffs[f['feature']]['b'][i]
                                )
                    else:
                        norm_value = f['value']
                else:
                    norm_value = f['value']
                filter += " " + prepend_value_label(f) + f['feature'] + "=" + str(norm_value) + " "

            else:
                filter += " "
                if f['value']['min'] is not None:
                    if coeffs:
                        if '[' in f['feature']:
                            # if character [ is in feature name it means that is multidimensional filter
                            f_name = f['feature'].split('[')[0]
                            f_dimension = int(f['feature'].split('[')[1].split(']')[0])
                            norm_value = coeffs[f_name]['a'][f_dimension] * f['value']['min'] + coeffs[f_name]['b'][
                                f_dimension]
                        else:
                            norm_value = coeffs[f['feature']]['a'][0] * f['value']['min'] + coeffs[f['feature']]['b'][0]
                    else:
                        norm_value = f['value']['min']
                    filter += prepend_value_label(f) + f['feature'] + ">" + str(norm_value) + " "
                if f['value']['max'] is not None:
                    if f['value']['min'] is not None:
                        filter += "AND "
                    if coeffs:
                        if '[' in f['feature']:
                            # if character [ is in feature name it means that is multidimensional filter
                            f_name = f['feature'].split('[')[0]
                            f_dimension = int(f['feature'].split('[')[1].split(']')[0])
                            norm_value = coeffs[f_name]['a'][f_dimension] * f['value']['max'] + coeffs[f_name]['b'][
                                f_dimension]
                        else:
                            norm_value = coeffs[f['feature']]['a'][0] * f['value']['max'] + coeffs[f['feature']]['b'][0]
                    else:
                        norm_value = f['value']['max']
                    filter += prepend_value_label(f) + f['feature'] + "<" + str(norm_value) + " "

    return filter


def parse_target(target_string, layout_descriptor_names):
    ALLOWED_CONTENT_BASED_SEARCH_DESCRIPTORS = layout_descriptor_names
    target_struct = {}

    min_pos = 0
    while target_string.find(':', min_pos) != -1:
        current_pos = target_string.find(':', min_pos)
        min_pos = current_pos + 1

        # Left part (feature name)
        previous_space_pos = target_string.rfind(' ', 0, current_pos)
        feature_name = target_string[previous_space_pos + 1:current_pos]
        if feature_name[0] != '.':
            feature_name = '.' + feature_name

        if feature_name not in ALLOWED_CONTENT_BASED_SEARCH_DESCRIPTORS:
            return 'Target error: At least one feature name does not match with any descirptor name in our database or the matched descriptor can not be used as target (' + str(
                feature_name
            ) + '). '

        # Right part
        next_space_pos = target_string.find(' ', current_pos + 1)
        if next_space_pos == -1:
            next_space_pos = len(target_string)
        right_part = target_string[current_pos + 1:next_space_pos + 1]
        if not "," in right_part:
            try:
                value = float(right_part)
            except:
                return 'Target error: Using non-numerical descriptor values in target parameter.'
        else:
            try:
                value = [float(x) for x in right_part.split(',')]
            except:
                return 'Target error: Using non-numerical descriptor values in target parameter.'

        target_struct[feature_name] = value

    return target_struct


def parse_metric_descriptors(metric_descriptors_string, layout_descriptor_names):
    return list(set(metric_descriptors_string.split(',')).intersection(layout_descriptor_names))


### Functions to generate a structured dictionary from a list of descriptor names


def create_nested_structure_of_dicts_from_list_of_keys(dict, keys):
    dict_aux = dict
    for count, key in enumerate(keys):
        if key not in dict_aux:
            if count == len(keys) - 1:
                dict_aux[key] = None
            else:
                dict_aux[key] = {}
        dict_aux = dict_aux[key]


def generate_structured_dict_from_layout(layout_descriptor_names):
    names = sorted(layout_descriptor_names)
    structure = dict()
    for name in names:
        create_nested_structure_of_dicts_from_list_of_keys(structure, name.split('.')[1:])
    return structure


def get_nested_dictionary_value(keys, dict):
    if keys[0] in dict:
        if len(keys) == 1:
            return dict[keys[0]]
        else:
            return get_nested_dictionary_value(keys[1:], dict[keys[0]])
    else:
        return None


def set_nested_dictionary_value(keys, dict, value):
    if len(keys) == 1:
        dict[keys[0]] = value
    else:
        set_nested_dictionary_value(keys[1:], dict[keys[0]], value)


def get_nested_descriptor_names(structured_layout, accumulated_list=[], keys=[]):
    for key, item in structured_layout.items():
        if isinstance(item, dict):
            keys.append(key)
            get_nested_descriptor_names(item, accumulated_list, keys)
        else:
            keys.append(key)
            accumulated_list.append('.'.join(keys))
        keys.pop()
