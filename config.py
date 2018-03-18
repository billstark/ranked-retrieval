import re

INVALID_CHARS = re.compile(r'[^\w\d\s\-]+')
INVALID_QUERY_CHARS = re.compile(r'[^\w\d\s()]+')
OPERATORS = {
    'OR': 1,
    'AND': 2,
    'NOT': 3,
    '(': 4,
    ')': 4,
}
UNARY_OPERATORS = {'NOT'}
