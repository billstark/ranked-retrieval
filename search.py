#!/usr/bin/python
import re
import nltk
import math
import sys
import getopt
from config import *
from operator import attrgetter, methodcaller


def usage():
    print "usage: " + sys.argv[0] + " -d dictionary-file -p postings-file -q file-of-queries -o output-file-of-results"


# Create stemmer object
ps = nltk.stem.PorterStemmer()


class Postings:
    """Class used to interact with the posting and dictionary files"""

    def __init__(self, postings_filename, dictionary_filename):

        self.postings_file = open(postings_filename)
        # Cache parsed postings. If memory is tight, an LRU cache can be used instead.
        self.parsed_postings = dict()

        # Read in the dictionary file
        self.dictionary = dict()

        with open(dictionary_filename) as dictionary_file:
            doc_sizes_offset = int(dictionary_file.readline())
            for line in dictionary_file:
                try:
                    term, frequency, offset = line.split()
                    self.dictionary[term] = (int(frequency), int(offset))
                except ValueError:
                    pass

        self.doc_sizes, _ = self.parse_postings_and_doc_set(doc_sizes_offset, cache=False)

    def parse_postings_and_doc_set(self, offset, cache=True):
        """
        Returns the posting and skip pointers from a given offset in the postings file.
        Posting is returned as a list of document IDs, and skip pointer as a dictionary of index to index
        """
        if cache and offset in self.parsed_postings:
            return self.parsed_postings[offset]

        self.postings_file.seek(offset)
        postings_string = self.postings_file.readline()
        postings = dict()
        doc_set = set()

        for posting in postings_string.split():
            doc_freq_pair = posting.split(':')
            postings[int(doc_freq_pair[0])] = int(doc_freq_pair[1])
            doc_set.add(int(doc_freq_pair[0]))

        if cache:
            self.parsed_postings[offset] = postings, doc_set

        return postings, doc_set

    def get_posting_and_doc_set(self, query_term):
        """
        Return the posting and document id set for a specific term.
        """
        if query_term not in self.dictionary:
            return dict(), set()

        frequency, offset = self.dictionary[query_term]
        return self.parse_postings_and_doc_set(offset)


def get_query_result(query, postings):
    """Given query and posting object, return the top-ten related results"""
    parsed_query = parse_query(query)
    temp_result = get_all_doc_with_score(parsed_query, postings)

    # sort by id first
    temp_result = sorted(temp_result, key=lambda pair: pair[0])

    # then sort by score
    temp_result = sorted(temp_result, key=lambda pair: pair[1], reverse=True)
    result = map(lambda data: data[0], temp_result[:10])
    return temp_result[:10]


def parse_query(query):
    """Parses a query into { term: freq } mapping"""

    result_dict = dict()
    for token in nltk.word_tokenize(query):
        # Remove invalid characters (punctuations, special characters, etc.)
        token = re.sub(INVALID_CHARS, "", token)

        if not token:
            continue

        term = ps.stem(token.lower())
        if term in result_dict:
            result_dict[term] += 1
        result_dict[term] = 1
    return result_dict


def get_all_doc_with_score(parsed_query, postings):
    """Gets all the documents with their corresponding scores

    Result would be in the form of { doc_id: score }
    """

    # parse all the terms
    query_terms = parsed_query.keys()

    # calcualte the ltc based on terms
    ltc_list = calculate_query_ltc(parsed_query, query_terms, postings)

    # here is a small optimization, I get all the related documents (contains at least
    # one query term) to get result
    related_docs = list(get_query_related_doc_set(query_terms, postings))

    result = list()

    # calcualte scores one by one
    for doc_id in related_docs:
        result.append((doc_id, calculate_doc_score(doc_id, query_terms, postings, ltc_list)))

    return result


def get_query_related_doc_set(query_terms, postings):
    """Gets a set of documents that contains at least one query term
    Returns a set of doc_id
    """
    result_set = set()
    for term in query_terms:
        _, doc_set = postings.get_posting_and_doc_set(term)
        result_set = result_set.union(doc_set)
    return result_set


def calculate_doc_score(doc_id, query_terms, postings, query_ltc_list):
    """Calculates the score for a specific document"""
    score = 0

    # gets the lnc for the document
    lnc_list = calculate_doc_lnc(doc_id, query_terms, postings)

    # then just do multiplication and divide the score by the doc size
    for index, lnc_weight in enumerate(lnc_list):
        score += lnc_weight * query_ltc_list[index]
    return score / postings.doc_sizes[doc_id]


def calculate_doc_lnc(doc_id, query_terms, postings):
    """Gets the lnc weights document-related terms"""
    lnc_list = list()
    sum_of_square = 0
    for index, query_term in enumerate(query_terms):

        # gets the posting for this specific term
        posting, _ = postings.get_posting_and_doc_set(query_term)
        if doc_id not in posting:
            lnc_list.append(0)
            continue

        # gets the tf and calculate log
        lnc_list.append(1 + math.log(posting[doc_id], 10))
        sum_of_square += math.pow(lnc_list[index], 2)

    # do normalization
    lnc_list = map(lambda data: data / math.sqrt(sum_of_square), lnc_list)
    return lnc_list


def calculate_query_ltc(parsed_query, query_terms, postings):
    """Gets the ltc weights for query terms"""
    ltc_list = list()
    sum_of_square = 0
    total_num_of_docs = len(postings.doc_sizes)
    for index, query_term in enumerate(query_terms):

        # if the term even never exists in the dictionary, just skip
        if query_term not in postings.dictionary:
            ltc_list.append(0)
            continue

        # else, calculate tf.idf and normalize it (which is not neccessary)
        ltc_list.append(1 + math.log(parsed_query[query_term], 10))
        idf = math.log(total_num_of_docs / postings.dictionary[query_term][0], 10)
        ltc_list[index] *= idf
        sum_of_square += math.pow(ltc_list[index], 2)

    # this can be ignored. for now I just to the normalization
    ltc_list = map(lambda data: data / math.sqrt(sum_of_square), ltc_list)
    return ltc_list


dictionary_file = postings_file = file_of_queries = file_of_output = None

try:
    opts, args = getopt.getopt(sys.argv[1:], 'd:p:q:o:')
except getopt.GetoptError, err:
    usage()
    sys.exit(2)

for o, a in opts:
    if o == '-d':
        dictionary_file = a
    elif o == '-p':
        postings_file = a
    elif o == '-q':
        file_of_queries = a
    elif o == '-o':
        file_of_output = a
    else:
        assert False, "unhandled option"

if dictionary_file is None or postings_file is None or file_of_queries is None or file_of_output is None:
    usage()
    sys.exit(2)

query_file = open(file_of_queries)
output_file = open(file_of_output, 'w')

postings = Postings(postings_file, dictionary_file)
get_query_result('tax operation', postings)

for line in query_file:
    result = get_query_result(line.stripe(), postings)
    output_file.write(" ".join(result) + "\n")
