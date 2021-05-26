from pyparsing import CaselessLiteral, Word, alphanums, alphas8bit, nums, quotedString, \
    operatorPrecedence, opAssoc, removeQuotes, Literal, Group, White, Optional

alphanums_plus = alphanums + '_' + '"'  # Allow underscore character and " in filter name
float_nums = nums + '.'  # Allow float numbers
and_ = CaselessLiteral("and")
or_ = CaselessLiteral("or")
not_ = CaselessLiteral("not")
filterValueText = Word(alphanums_plus + alphas8bit + float_nums + '-') | quotedString.setParseAction(removeQuotes)
number_or_asterisk_or_quotedString = Literal('*') | Word(float_nums) | quotedString.setParseAction(removeQuotes)
filterValueRange = Literal('[') + number_or_asterisk_or_quotedString + White(' ', max=1) + Literal('TO') + White(' ', max=1) + number_or_asterisk_or_quotedString + Literal(']')
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
    if filter_query:
        return filterExpr.parseString(filter_query)[0]
    else:
        return []