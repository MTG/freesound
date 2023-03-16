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
import collections

import pyparsing as pp
from pyparsing import pyparsing_common as ppc


pp.ParserElement.enablePackrat()

COLON, LBRACK, RBRACK, LBRACE, RBRACE, TILDE, CARAT = list(map(pp.Literal, ":[]{}~^"))
LPAR, RPAR = list(map(pp.Literal, "()"))
and_, or_, not_, to_ = list(map(pp.CaselessKeyword, "AND OR NOT TO".split()))
keyword = and_ | or_ | not_ | to_

expression = pp.Forward()

valid_word = pp.Regex(
    r'([a-zA-Z0-9*_+.-]|\\\\|\\([+\-!(){}\[\]^"~*?:]|\|\||&&))+'
).setName("word")
valid_word.setParseAction(
    lambda t: t[0].replace("\\\\", chr(127)).replace("\\", "").replace(chr(127), "\\")
)

string = pp.QuotedString('"', unquoteResults=False)
alphanums_plus = pp.alphanums + '_'
float_nums = pp.nums + '.'
alphanum_float_plus_minus_star = alphanums_plus + float_nums + '+' + '-' + '*'

required_modifier = pp.Literal("+")("required")
prohibit_modifier = pp.Literal("-")("prohibit")
integer = ppc.integer()
proximity_modifier = pp.Group(TILDE + integer("proximity"))
number = ppc.fnumber()
fuzzy_modifier = TILDE + pp.Optional(number, default=0.5)("fuzzy")

term = pp.Forward().setName("field")
field_name = valid_word().setName("fieldname")
incl_range_search = pp.Group(LBRACK - term("lower") + to_ + term("upper") + RBRACK)
excl_range_search = pp.Group(LBRACE - term("lower") + to_ + term("upper") + RBRACE)
range_search = incl_range_search("incl_range") | excl_range_search("excl_range")
boost = CARAT - number("boost")

geotag_filter = pp.Literal("'{!") + pp.Word(' ' + '=' + ',' + alphanum_float_plus_minus_star) + pp.Literal("}'")
string_expr = pp.Group(string + proximity_modifier) | string
word_expr = pp.Group(valid_word + fuzzy_modifier) | valid_word
term << (
    pp.Optional(field_name("field") + COLON)
    + (word_expr | string_expr | range_search | pp.Group(LPAR + expression + RPAR))
    + pp.Optional(boost)
)
term.setParseAction(lambda t: [t] if "field" in t or "boost" in t else None)

expression << pp.infixNotation(
    pp.Group(term | geotag_filter),
    [
        (required_modifier | prohibit_modifier, 1, pp.opAssoc.RIGHT),
        ((not_ | "!").setParseAction(lambda: "NOT"), 1, pp.opAssoc.RIGHT),
        ((and_ | "&&").setParseAction(lambda: "AND"), 2, pp.opAssoc.LEFT),
        (
            pp.Optional(or_ | "||").setName("or"),
            2,
            pp.opAssoc.LEFT,
        ),
    ],
)


def flatten(l):
    for el in l:
        if isinstance(el, collections.abc.Iterable) and not isinstance(el, str):
            yield from flatten(el)
        else:
            # for range filter with TO, we manually add the mandatory spaces in the parsed output
            if el == 'TO':
                yield ' ' + el + ' '
            else:
                yield el


def flatten_sub(l):
    return [list(flatten(sub)) for sub in l]


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
        try:
            filter_list_str = expression.parseString(filter_query).asList()[0]
        except pp.ParseSyntaxException:
            return []

        # check if not nested meaning there is only one filter
        # if yes, make it nested to treat it the same way as if there were several filters
        if isinstance(filter_list_str[0], str):
            filter_list_str = [filter_list_str]

        # we flatten the sub lists contained in the parsed output
        filter_list_str = flatten_sub(filter_list_str)

        # remove empty filter values
        filter_list_str = [
            filter_str for filter_str in filter_list_str if filter_str[-1] != ":"
        ]
        return filter_list_str
    else:
        return []
