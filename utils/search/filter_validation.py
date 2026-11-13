import math
from collections.abc import Iterable

import luqum.thread
import luqum.tree

from utils.search import escape_lucene_phrase_value

FIELD_TYPES_MAP = {
    "samplerate": int,
    "bitrate": int,
    "bitdepth": int,
    "channels": int,
    "duration": float,
    "filesize": int,
    "num_downloads": int,
    "avg_rating": float,
    "num_ratings": int,
    "num_comments": int,
    "timestamp_start": float,
    "timestamp_end": float,
}


def quote_filter_value(value: str) -> str:
    """Quote a literal filter value, escaping backslashes and double quotes."""
    return '"' + escape_lucene_phrase_value(value) + '"'


def normalize_numeric_value(field_name: str, value: str) -> str:
    """Check one value against the field's numeric type and return it as a string.

    If the type is a float, accept a comma as a decimal separator: treat
    1,4 as 1.4 and try again. Accept "*" as it's used in range bounds.

    Returns the normalized value as a string.
    Raises ValueError if the value is not a numeric value.
    """
    expected_type = FIELD_TYPES_MAP[field_name]
    normalized = value.strip()
    if normalized == "*":
        return normalized
    try:
        try:
            number = expected_type(normalized)
        except ValueError:
            if expected_type is not float or "," not in normalized:
                raise
            normalized = normalized.replace(",", ".")
            number = float(normalized)
        if expected_type is int or math.isfinite(number):
            return normalized
    except (ValueError, OverflowError):
        pass
    raise ValueError(f"Filter parsing error: '{field_name}' value must be {expected_type.__name__}, got {value!r}")


def parse_filter(filter_string):
    """Parse a Lucene-style filter string into its list of top-level nodes.
    Empty string -> []. Raises luqum.exceptions.ParseError on malformed input.
    """
    if not filter_string:
        return []
    # use thread-safe parser
    tree = luqum.thread.parse(filter_string)
    return [tree] if type(tree) == luqum.tree.SearchField else tree.children


def validate_numeric_filters(nodes: Iterable[luqum.tree.Item]) -> str | None:
    """Validate numeric fields in the luqum nodes returned by parse_filter.

    Args:
        nodes: A parsed luqum nodes for a user query, such as
            'duration:[0 TO 10] samplerate:44100'.

    Walks `nodes` and for every field which we know should be numeric, use
    normalize_numeric_value to check that it is valid.
    If a numeric field is updated to make it valid, the nodes are updated in-place.

    Return the first error message, or None if all numeric values are valid.
    """

    def validate(node, field_name=None):
        if isinstance(node, luqum.tree.SearchField):
            if field_name in FIELD_TYPES_MAP:
                # A numeric value cannot contain another field.
                normalize_numeric_value(field_name, str(node))
            field_name = node.name
        if field_name in FIELD_TYPES_MAP and isinstance(node, (luqum.tree.Word, luqum.tree.Phrase)):
            quoted = isinstance(node, luqum.tree.Phrase)
            value = node.value[1:-1] if quoted else node.value
            normalized = normalize_numeric_value(field_name, value)
            node.value = f'"{normalized}"' if quoted else normalized
        else:
            for child in node.children:
                validate(child, field_name)

    try:
        for node in nodes:
            validate(node)
    except ValueError as error:
        return str(error)
    return None


def find_dropped_filters(nodes) -> list[str]:
    """Return a list of human-readable representations of filters that
    SearchQueryProcessor would silently drop.

    Hand-made URLs sometimes use `%2B` instead of a space between filters, which
    decodes as a `+` instead of a space. Lucene reads that `+` as a MUST prefix,
    so the following filter parses as a top-level Plus-wrapped node:

        sent:     f=tag%3A%22tap%22%2Busername%3A%22ascap%22
        decoded:  tag:"tap"+username:"ascap"
        expected: tag:"tap" username:"ascap"
        parsed:   [SearchField('tag', '"tap"'), Plus(SearchField('username', '"ascap"'))]
        expected  [SearchField('tag', '"tap"'), SearchField('username', '"ascap"')]

    SearchQueryProcessor currently drops the second part of the search query, so
    this function returns ['username:"ascap"'].

    Empty list means nothing was removed.
    """
    dropped = []
    for node in nodes:
        if isinstance(node, luqum.tree.Plus) and isinstance(node.a, luqum.tree.SearchField):
            # str() of a luqum node can keep trailing whitespace from the source string
            dropped.append(str(node.a).strip())
    return dropped
