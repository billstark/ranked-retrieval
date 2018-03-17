This is the README file for A0135817B and A0147995H's submission

Email address:
e0011848@u.nus.edu
e0012667@u.nus.edu

== Python Version ==

We're using Python Version 2.7.14 for this assignment.

== General Notes about this assignment ==

## Indexing:

Procedure:

  1. For every training file, load the whole content into the system and tokenize into words
  2. Remove invalid characters of the tokenized word
  3. Add the word into the posting list
  4. Format postings and add skip pointers every sqrt(n) postings.
  5. Write postings into the posting file
  6. Write terms into dictionary file with offset to the corresponding postings.

Notes:

  1. We choose not to use sentence tokenizer because we are handle invalid punctuation by keeping only
     digits, alphabets, white spaces and dashes
  2. We are using set to remove duplicated document IDs
  3. the posting is in the format of `docId:pointer` if there is a skip pointer, or just `docId`
     if there isn't. Postings are delimited by space
  5. We write a posting with all file names at the end of the posting file just for NOT operation
  6. At the first line in the dictionary file we write the offset for all postings

Searching:
 - The entire dictionary is read into memory
 - The query is parsed into an AST using Dijkstra's Shunting-yard Algorithm. Some simple
   optimization is applied, such as
    - Removing NOT NOT (as these do not have any effect)
    - Turning (NOT a OR NOT b) into NOT (a AND b), which is likely to be faster
 - The AST is recursively "collapsed" as we walk down to each operation node and apply them
    - At the leaf nodes, we retrieve the posting from the file. The posting is then cached
      so that repeated queries against the same terms do not need to hit the file system
    - For each of the operations, we use O(n) time algorithm to merge the child posting lists
      to produce a new posting list
 - These optimizations are applied to the merge algorithm for the AND operation
    - Start with the shortest posting
    - Use skip pointers if they are available
    - When an AND NOT operation is detected, use set difference to improve computation performance
 - NOT and OR operations are implemented relatively naively as we do not see any easy optimizations


== Files included with this submission ==

config.py       - includes regex and some constants that will be used in index.py and search.py.
index.py        - indexing program that will be run to index all the training files.
search.py       - searching program that will be used to execute queries in a specific file and give output.
dictionary.txt  - a dictionary mapping terms to their location in the postings file
postings.txt    - includes document IDs for each term

== Statement of individual work ==

Please initial one of the following statements.

[X] We, A0135817B and A0147995H, certify that I have followed the CS 3245 Information
Retrieval class guidelines for homework assignments.  In particular, I
expressly vow that I have followed the Facebook rule in discussing
with others in doing the assignment and did not take notes (digital or
printed) from the discussions.  

[ ] I, A0000000X, did not follow the class rules regarding homework
assignment, because of the following reason:

<Please fill in>

I suggest that I should be graded as follows:

<Please fill in>

== References ==

- Shunting-yard algorithm: https://en.wikipedia.org/wiki/Shunting-yard_algorithm
- The Shunting-Yard Algorithm - Nathan Reed's coding blog: http://reedbeta.com/blog/the-shunting-yard-algorithm/
- Introduction to Information Retrieval
  - Faster postings list intersection via skip pointers