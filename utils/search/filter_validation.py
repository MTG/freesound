import luqum.tree
from luqum.parser import parser

FIELD_TYPES_MAP = {
    "samplerate": int,
    "bitrate": int,
    "bitdepth": int,
    "channels": int,
    "duration": float,
}

COMPLEX_EXPR_TYPES = (
    luqum.tree.Range,
    luqum.tree.OpenRange,
    luqum.tree.From,
    luqum.tree.To,
    luqum.tree.FieldGroup,
    luqum.tree.Boost,
)


def parse_filter(filter_string):
    """Parse a Lucene-style filter string into its list of top-level nodes.
    Empty string -> []. Raises luqum.exceptions.ParseError on malformed input.
    """
    if not filter_string:
        return []
    tree = parser.parse(filter_string)
    return [tree] if type(tree) == luqum.tree.SearchField else tree.children


def validate_filter_types(nodes) -> str | None:
    """Validate that in the given top-level filter nodes, the values of fields
    with a known type (FIELD_TYPES_MAP) can be cast to that type. Return a
    human-readable error string on first failure, or None on success.
    """
    for node in nodes:
        if type(node) != luqum.tree.SearchField:
            continue
        if node.name not in FIELD_TYPES_MAP:
            continue
        expr = node.expr
        if isinstance(expr, COMPLEX_EXPR_TYPES):
            # Ranges/inequalities/groups/boosts etc. e.g. samplerate:[a TO b]
            # validate directly in solr
            continue
        if isinstance(expr, luqum.tree.Phrase):
            # String in "quotes"
            value = expr.value[1:-1]
        else:
            value = str(expr)
        if value == "*":
            # `field:*` is a valid solr query, continue
            continue
        expected_type = FIELD_TYPES_MAP[node.name]
        # This does let through some values that are valid in python but not solr
        # (e.g. int(1_000)), but we accept these few cases because they are rare
        try:
            expected_type(value)
        except (ValueError, TypeError):
            return f"Filter parsing error: '{node.name}' value must be {expected_type.__name__}, got {value!r}"
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
