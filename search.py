#!/usr/bin/python
import re
import nltk
import math
import sys
import getopt
import threading
from common import tokenize
from operator import attrgetter, methodcaller, itemgetter
from collections import Counter
from pprint import pprint


def usage():
    print "usage: " + sys.argv[0] + " -d dictionary-file -p postings-file -q file-of-queries -o output-file-of-results"

class DocScoreHeap:

    def __init__ (self):
        self.heap = []
        self.size = 0

    def push(self, doc_score_pair):
        index = self.size
        self.heap.append(doc_score_pair)
        self.__swap_up(index)
        self.size += 1

    def pop(self):
        if self.size <= 0:
            return ()
        self.heap[0], self.heap[self.size - 1] = self.heap[self.size - 1], self.heap[0]
        data = self.heap[self.size - 1]
        del self.heap[-1]
        self.size -= 1
        self.__swap_down(0)
        return data

    def __swap_up(self, index):
        while index > 0:
            parent_index = int((index - 1) / 2)
            if self.heap[index][1] < self.heap[parent_index][1] or (self.heap[index][1] == self.heap[parent_index][1] and self.heap[index][0] > self.heap[parent_index][0]):
                return
            self.heap[index], self.heap[parent_index] = self.heap[parent_index], self.heap[index]
            index = parent_index

    def __swap_down(self, index):
        while index <= int((len(self.heap) - 2) / 2):
            max_child = self.__max_child(index)
            if self.heap[index][1] > self.heap[max_child][1] or (self.heap[index][1] == self.heap[max_child][1] and self.heap[index][0] < self.heap[max_child][0]):
                return
            self.heap[index], self.heap[max_child] = self.heap[max_child], self.heap[index]
            index = max_child

    def __max_child(self, index):
        left_child = 2 * index + 1
        right_child = 2 * index + 2
        if right_child > self.size - 1:
            return left_child

        if self.heap[left_child][1] > self.heap[right_child][1]:
            return left_child

        if self.heap[left_child][1] < self.heap[right_child][1]:
            return right_child

        if self.heap[left_child][0] > self.heap[right_child][0]:
            return right_child

        return left_child

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
    get_all_doc_with_score(parsed_query, postings)
    result_list = []

    for i in range(0, count):
        result_list.append(pq.pop()[0])

    return result_list

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

def calculate_splited_doc_score(doc_ids, query_terms, postings, ltc_list):
    for doc_id in doc_ids:
        score = calculate_doc_score(doc_id, query_terms, postings, ltc_list)
        doc_heap_lock.acquire()
        pq.push((doc_id, score))
        doc_heap_lock.release()

def get_all_doc_with_score(parsed_query, postings, num_of_threads=10):
    """Gets all the documents with their corresponding scores

    Result would be in the form of { doc_id: score }
    """

    # parse all the terms
    query_terms = parsed_query.keys()

    # Calculate the ltc based on terms
    ltc_list = calculate_query_ltc(parsed_query, query_terms, postings)

    # Small optimization: get all the related documents (contains at least one query term) to get result
    related_docs = get_query_related_doc_set(query_terms, postings)

    # splits related docs into small blocks so that we could do multithreading
    splited_docs = split_list(list(related_docs), num_of_threads)

    threads = []

    # for each data block, put it into a thead to calculate their scores
    for splited_block in splited_docs:
        calculate_thread = threading.Thread(target=calculate_splited_doc_score, args=(splited_block, query_terms, postings, ltc_list))
        threads.append(calculate_thread)
        calculate_thread.start()

    # wait for all thread to complete the task
    for thread in threads:
        thread.join()


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

# query_file = open(file_of_queries)
# output_file = open(file_of_output, 'w')

postings = Postings(postings_file, dictionary_file)
pq = DocScoreHeap()
doc_heap_lock = threading.Lock()
print(get_query_result('tax operation', postings))

# for line in query_file:
#     result = get_query_result(line.strip(), postings)
#     output_file.write(" ".join(result) + "\n")
