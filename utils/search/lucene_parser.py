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

from pyparsing import CaselessLiteral, Word, alphanums, alphas8bit, nums, quotedString, \
    operatorPrecedence, opAssoc, removeQuotes, Literal, Group, White, Optional, ParseException


alphanums_plus = alphanums + '_' + '"'  # Allow underscore character and " in filter name
float_nums = nums + '.'  # Allow float numbers
and_ = CaselessLiteral("and")
or_ = CaselessLiteral("or")
not_ = CaselessLiteral("not")
filterValueText = Word(alphanums_plus + alphas8bit + float_nums + '-') | quotedString.setParseAction(removeQuotes)
number_or_asterisk_or_quotedString = Literal('*') | Word(float_nums) | quotedString.setParseAction(removeQuotes)
filterValueRange = Literal('[') + number_or_asterisk_or_quotedString + White(' ', max=1) + Literal('TO') \
                   + White(' ', max=1) + number_or_asterisk_or_quotedString + Literal(']')
fieldName = Word(alphanums_plus)
filterTerm = fieldName + Literal(':') + (filterValueText | filterValueRange)
filterExpr = operatorPrecedence(Group(filterTerm),
                                [
                                    (not_, 1, opAssoc.RIGHT),
                                    (and_, 2, opAssoc.LEFT),
                                    (or_, 2, opAssoc.LEFT),
                                    (Optional(or_ | "||").setName("or"), 2, opAssoc.LEFT),
                                ])


def parse_query_filter_string(filter_query):
    """Parse the query filter string containing field names and values.

    This is useful for for being able to manipulate different filters and removing filters coming 
    from facets (which is needed for applying clustering without being affected by filtering facets).

    Example:
    f = " duration:[1 TO *] is_geotagged:1 tag:dog"
    parse_query_filter_string(f)
    -> ([(['duration', ':', '[', '1', ' ', 'TO', ' ', '*', ']'], {}), 
         (['is_geotagged', ':', '1'], {}), (['tag', ':', 'dog'], {})], {})

    Args:
        filter_query (str): query filter string from a user submitted search query.
    
    Returns:
        pyparsing.ParseResults: can be treated as a list containing lists of filter fields' names and values
    """
    if filter_query:
        try:
            return filterExpr.parseString(filter_query)[0]
        except ParseException:
            return []
    else:
        return []
