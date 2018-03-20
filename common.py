import nltk
import re

INVALID_CHARS = re.compile(r'[^\w\d\s\-]+')
ps = nltk.stem.PorterStemmer()


def tokenize(text):
    """Return a list of sanitized tokens from the given text"""
    tokens = map(lambda t: re.sub(INVALID_CHARS, "", t), nltk.word_tokenize(text))
    return map(lambda t: ps.stem(t.lower()), filter(None, tokens))
