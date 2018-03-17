#!/usr/bin/python
import re
import nltk
import sys
import getopt
import math
import os
from config import *
from collections import defaultdict

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
#    - A postings list is build in word_postings as { word: { doc_id, doc_id, ...} }.
#      A set is used to deduplicate terms appearing multiple times in the same document.
# 2. Posting list is written to postings.txt in alphabetical order with each posting appearing
#    on its own line, and each document ID delimited by spaces.
#    - Skip pointers are inserted after every sqrt(n) posting. They appear as 'doc_id:pointer',
#      with the pointer pointing towards the index of the skip index
#    - As the list is written the offset for each term appearing in the document is stored
#      in word_offsets
# 3. The dictionary file is written to dictionary.txt, with each term appearing alphabetically
#    on their own line. The format is 'term offset frequency'.


# Create stemmer object
ps = nltk.stem.PorterStemmer()

# words is a set of (word, document_id)
word_postings = defaultdict(set)

all_doc_ids = sorted(map(int, os.listdir(input_directory)))

for doc_id in all_doc_ids:
    filepath = os.path.join(input_directory, str(doc_id))
    with open(filepath) as input_file:
        document_content = input_file.read()
        for word in nltk.word_tokenize(document_content):
            # Remove invalid characters (punctuations, special characters, etc.)
            word = re.sub(INVALID_CHARS, "", word)

            if not word:
                continue

            # Stem and lowercase the word
            word = ps.stem(word.lower())
            word_postings[word].add(doc_id)


def format_posting_list(posting):
    # Ensure the document IDs are sorted
    posting = sorted(posting)

    # Calculates the number of index per skip
    skip = int(math.sqrt(len(posting)))

    # Keep track of the next skip pointer index
    next_index = 0
    posting_strings = []

    for index, doc_id in enumerate(posting):
        # If the current index is the next index, we reach a skip point
        if index == next_index and index != len(posting) - 1:
            # If the next skip point exceeds the total length, just let the next_index to be the last index
            if index + skip >= len(posting):
                next_index = len(posting) - 1
            else:
                next_index = index + skip

            posting_strings.append("{}:{}".format(doc_id, next_index))
        else:
            posting_strings.append(str(doc_id))

    return " ".join(posting_strings) + "\n"


# Sort the words so that they appear in the dictionary in alphabetical order
word_list = sorted(word_postings)
word_offsets = {}

with open(output_file_postings, 'w') as posting_file:
    # Keep track of the offset from the start of the file
    offset = 0

    for word in word_list:
        posting_list = format_posting_list(word_postings[word])
        word_offsets[word] = offset
        offset += len(posting_list)

        # writes into posting
        posting_file.write(posting_list)

    # This is to add all postings (a posting of all existing doc ids)
    posting_file.write(format_posting_list(all_doc_ids))
    posting_file.close()

# writes into dictionary
# add this offset for the last posting (all postings)
with open(output_file_dictionary, 'w') as dictionary_file:
    dictionary_file.write(str(offset) + "\n")

    for word in word_list:
        dictionary_file.write("{} {} {}\n".format(word, word_offsets[word], len(word_postings[word])))

    dictionary_file.close()
