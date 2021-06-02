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

import sys

from pyparsing import CaselessLiteral, Word, alphanums, alphas8bit, nums, printables, \
        operatorPrecedence, opAssoc, Literal, Group, White, Optional, ParseException, Empty


# get all unicodes (https://stackoverflow.com/questions/2339386/python-pyparsing-unicode-characters)
unicode_printables = u''.join(unichr(c) for c in xrange(sys.maxunicode) if not unichr(c).isspace())
printables_less = unicode_printables.replace('"', '')
alphanums_plus = alphanums + '_'
float_nums = nums + '.'
or_ = CaselessLiteral("or")

# filter value without ""
filter_value_text = Word(alphanums_plus + alphas8bit + float_nums + '-' + '+' + ',')

# filter value with "" (any character including spaces)
filter_value_text_with_spaces = Literal('"') + Word(' ' + printables_less) + Literal('"')

# case for treating eg, 'license:("Attribution" OR "Creative Commons 0")'
filter_value_text_with_parentheses = Literal('(') + Word(' "' + printables_less.replace('(','').replace(')', '')) + Literal(')')

# for float ranged values
alphanum_float_plus_minus_star = alphanums_plus + float_nums + '+' + '-' + '*'
filter_value_range = Literal('[') + Word(alphanum_float_plus_minus_star) + White(' ', max=1) + Literal('TO') \
                    + White(' ', max=1) + Word(alphanum_float_plus_minus_star) + Literal(']')

geotag_filter = Literal("'{!") + Word(' ' + '=' + ',' + alphanum_float_plus_minus_star) + Literal("}'")

field_name = Word(alphanums_plus)
filter_term = field_name + Literal(':') + (filter_value_text | filter_value_text_with_spaces | filter_value_text_with_parentheses | filter_value_range | Empty())
filter_expr = operatorPrecedence(Group(filter_term | geotag_filter), [(Optional(or_ | "||").setName("or"), 2, opAssoc.LEFT)])


def parse_query_filter_string(filter_query):
    """Parse the query filter string containing field names and values.

    This is useful for for being able to manipulate different filters and removing filters coming 
    from facets (which is needed for applying clustering without being affected by filtering facets).
    Additionally it removes filters that contain empty values.

    Example:
    f = " duration:[1 TO *] is_geotagged:1 tag:dog"
    parse_query_filter_string(f)
    -> [['duration', ':', '[', '1', ' ', 'TO', ' ', '*', ']'], 
        ['is_geotagged', ':', '1'], 
        ['tag', ':', 'dog']]

    Args:
        filter_query (str): query filter string from a user submitted search query.
    
    Returns:
        List[List[str]]: list containing lists of filter fields' names and values
    """
    if filter_query:
        filter_list_str = filter_expr.parseString(filter_query)[0].asList()
        # check if not nested meaning there is only one filter
        # if yes, make it nested to treat it the same way as if there were several filters
        if isinstance(filter_list_str[0], basestring):
            filter_list_str = [filter_list_str]

        # remove empty filter values
        filter_list_str = [
            filter_str for filter_str in filter_list_str if filter_str[-1] != ":"
        ]
        return filter_list_str
    else:
        return []
