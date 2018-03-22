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
  3. Count the term in a dictionary mapping document id to a term frequency counter
  4. Write postings into the posting file
  5. Write terms into dictionary file with offset to the corresponding postings.

Notes:

  - We choose not to use sentence tokenizer because we are handle invalid punctuation by keeping only
     digits, alphabets, white spaces and dashes

Searching:
 - The entire dictionary is read into memory
 - Each query is tokenized using the same method as for indexing
 - For each query term, we calculate their weights using 1 + log(tf)
 - For every document that any of the query terms appear in, we calculate the total score using the query weight
   and the document tf-idf
 - We collect the top 10 documents using a priority queue and return the result

== Files included with this submission ==

common.py       - includes the tokenization function which is used for both index and search
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

- tf-idf
