#!/usr/bin/python
import math
import sys
import getopt
import heapq
from multiprocessing import Pool
from common import tokenize
from collections import Counter


def usage():
    print "usage: " + sys.argv[0] + " -d dictionary-file -p postings-file -q file-of-queries -o output-file-of-results"


class Postings:
    """Class used to interact with the posting and dictionary files"""

    def __init__(self, postings_filename, dictionary_filename):
        self.postings_file = open(postings_filename)

        # Cache parsed postings. If memory is tight, an LRU cache can be used instead.
        self.parsed_postings = {}

        # Read in the dictionary file
        self.dictionary = {}

        with open(dictionary_filename) as dictionary_file:
            doc_sizes_offset = int(dictionary_file.readline())
            for line in dictionary_file:
                try:
                    term, frequency, offset = line.split()
                    self.dictionary[term] = (int(frequency), int(offset))
                except ValueError:
                    pass

        self.doc_sizes = self.parse_posting(doc_sizes_offset, cache=False)

    def parse_posting(self, offset, cache=True):
        """Returns the posting and documents set from a given offset in the postings file.
        Posting is returned as a dictionary of document ID to the term's frequency in the document
        """
        if cache and offset in self.parsed_postings:
            return self.parsed_postings[offset]

        self.postings_file.seek(offset)
        postings_string = self.postings_file.readline()
        postings = {}

        for posting in postings_string.split():
            doc_id, doc_freq = map(int, posting.split(':'))
            postings[doc_id] = doc_freq

        if cache:
            self.parsed_postings[offset] = postings

        return postings

    def __getitem__(self, item):
        """Return the posting and document id set for a specific term."""
        if item not in self.dictionary:
            return dict()

        _, offset = self.dictionary[item]
        return self.parse_posting(offset)

    def __len__(self):
        return len(self.dictionary)

    def __contains__(self, item):
        return item in self.dictionary


def get_query_result(query, postings, count=10):
    """Given query and posting object, return the top-ten related results"""
    parsed_query = parse_query(query)
    pq = get_all_doc_with_score(parsed_query, postings)
    heapq.heapify(pq)

    results = []
    while pq and len(results) < count:
        _, doc_id = heapq.heappop(pq)
        results.append(doc_id)

    return results


def parse_query(query):
    """Parses a query into { term: freq } mapping"""
    return Counter(tokenize(query))


def split_list(lst, num_of_parts):
    result = []
    size = int(len(lst) / num_of_parts)
    while len(lst) > size:
        piece = lst[:size]
        result.append(piece)
        lst = lst[size:]
    result.append(piece)
    return result


def get_all_doc_with_score(parsed_query, postings):
    """Gets all the documents with their corresponding scores

    Result would be in the form of { doc_id: score }
    """

    # parse all the terms
    query_terms = parsed_query.keys()

    # Calculate the ltc based on terms
    ltc_list = calculate_query_ltc(parsed_query, query_terms, postings)

    # Small optimization: get all the related documents (contains at least one query term) to get result
    related_docs = get_query_related_doc_set(query_terms, postings)

    pq = []
    for doc_id in related_docs:
        score = calculate_doc_score(doc_id, query_terms, postings, ltc_list)
        pq.append((-score, doc_id))

    return pq


def get_query_related_doc_set(query_terms, postings):
    """Gets a set of documents that contains at least one query term
    Returns a set of doc_id
    """
    result_set = set()
    for term in query_terms:
        term_postings = postings[term]
        result_set = result_set.union(term_postings.keys())
    return result_set


def normalize(lst):
    rms = math.sqrt(sum(i * i for i in lst))
    if rms == 0:
        return lst
    return map(lambda i: i / rms, lst)


def calculate_doc_score(doc_id, query_terms, postings, query_weights):
    """Calculates the score for a specific document"""
    # gets the lnc for the document
    doc_weights = calculate_doc_lnc(doc_id, query_terms, postings)

    # then just do multiplication and divide the score by the doc size
    score = sum(doc * query for doc, query in zip(doc_weights, query_weights))
    return score / postings.doc_sizes[doc_id]


def calculate_doc_lnc(doc_id, query_terms, postings):
    """Gets the lnc weights document-related terms"""
    lnc_list = []

    for index, query_term in enumerate(query_terms):
        # Get the posting for this specific term
        posting = postings[query_term]
        if doc_id not in posting:
            lnc_list.append(0)
        else:
            # Gets the tf and calculate log
            lnc_list.append(1 + math.log10(posting[doc_id]))

    # Do normalization
    return normalize(lnc_list)


def calculate_query_ltc(parsed_query, query_terms, postings):
    """Gets the ltc weights for query terms"""
    ltc_list = []
    total_num_of_docs = len(postings)

    for index, query_term in enumerate(query_terms):
        if query_term not in postings:
            # Skip if the term does not even never appear in the dictionary
            ltc_list.append(0)
        else:
            # Calculate tf.idf and normalize it (which is not necessary)
            idf = math.log10(total_num_of_docs / postings.dictionary[query_term][0])
            ltc_list.append((1 + math.log10(parsed_query[query_term])) * idf)

    # this can be ignored. for now I just to the normalization
    return normalize(ltc_list)


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

if __name__ == '__main__':

    query_file = open(file_of_queries)
    output_file = open(file_of_output, 'w')

    pool = Pool(processes=4)

    postings = Postings(postings_file, dictionary_file)
    print(get_query_result('tax operation', postings))

    for line in query_file:
        result = get_query_result(line.strip(), postings)
        result = map(lambda doc_id: str(doc_id), result)
        output_file.write(" ".join(result) + "\n")
