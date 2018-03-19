#!/usr/bin/python
import re
import nltk
import sys
import getopt
import math
import os
from config import *
from collections import defaultdict, Counter


def usage():
    print "usage: " + sys.argv[0] + " -i directory-of-documents -d dictionary-file -p postings-file"


input_directory = output_file_dictionary = output_file_postings = None

try:
    opts, args = getopt.getopt(sys.argv[1:], 'i:d:p:')
except getopt.GetoptError, err:
    usage()
    sys.exit(2)

for o, a in opts:
    if o == '-i':  # input directory
        input_directory = a
    elif o == '-d':  # dictionary file
        output_file_dictionary = a
    elif o == '-p':  # postings file
        output_file_postings = a
    else:
        assert False, "unhandled option"

if input_directory is None or output_file_postings is None or output_file_dictionary is None:
    usage()
    sys.exit(2)

############################
# Implementation overview: #
############################

# It does the following things:
#
# 1. Read through all the training files and for each file, tokenize it to form terms
#    - We use word_tokenize to get words first, then sanitize it using our own regex
#      which removes most special characters, then use nltk stemmer to stem the words
#      and fold case to lowercase.
#    - word_tokenize is used because it performs better than our own algorithms, but
#      it is too permissive as it lets many unwanted special characters through, so we
#      separately sanitize it using our own regex.
#    - A postings list is build in term_dictionary as { term: { doc_id: freq, doc_id: freq, ...} }.
# 2. Posting list is written to `posting-file` in alphabetical order with each posting appearing
#    on its own line, and each document ID delimited by spaces. Each document ID is followed by
#    the term frequency in this document
# 3. The dictionary file is written to `dictionary-file`, with each term appearing alphabetically
#    on their own line. The format is 'term document_frequency offset'.


# Create stemmer object
ps = nltk.stem.PorterStemmer()

# a dictionary of the form { term: { docid: freq } }
term_dictionary = defaultdict(Counter)

all_doc_ids = sorted(map(int, os.listdir(input_directory)))

doc_size = dict()

for doc_id in all_doc_ids:
    print "Trying to index doc {}...".format(doc_id)
    filepath = os.path.join(input_directory, str(doc_id))

    with open(filepath) as input_file:
        document_content = input_file.read()
        unique_terms = 0
        for token in nltk.word_tokenize(document_content):
            # Remove invalid characters (punctuations, special characters, etc.)
            token = re.sub(INVALID_CHARS, "", token)

            if not token:
                continue

            # Stem and lowercase the word
            term = ps.stem(token.lower())

            if doc_id not in term_dictionary[term]:
                unique_terms += 1

            term_dictionary[term][doc_id] += 1

        doc_size[doc_id] = unique_terms
        input_file.close()


# Formats the posting list for a specific term
# - input: a posting of the form { doc_id: freq, doc_id: freq }
# - return: a formated posting string with "doc_id:freq doc_id:freq"
def format_posting_list(posting):
    sorted_doc_ids = sorted(posting)

    posting_strings = []

    for doc_id in sorted_doc_ids:
        posting_strings.append("{}:{}".format(doc_id, posting[doc_id]))

    return " ".join(posting_strings) + "\n"


sorted_terms = sorted(term_dictionary)
term_offsets = dict()

# writes all the postings
with open(output_file_postings, 'w') as posting_file:
    offset = 0

    for term in sorted_terms:
        posting_string = format_posting_list(term_dictionary[term])
        term_offsets[term] = offset
        offset += len(posting_string)

        posting_file.write(posting_string)

    posting_file.write(format_posting_list(doc_size))

# writes all the terms
with open(output_file_dictionary, 'w') as dictionary_file:
    dictionary_file.write(str(offset) + "\n")

    for term in sorted_terms:
        dictionary_string = "{} {} {}\n".format(term, len(term_dictionary[term]), term_offsets[term])
        dictionary_file.write(dictionary_string)
