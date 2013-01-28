
import numpy
from numpy import zeros, asarray
from scipy.linalg import svd
import unicodedata

from math import log

from nymag_scrape import connect_to_database

def get_stopwords():
    """
    Load the collection of stop words
    into memory
    """
    stop_words = set()
    with open('stop-words.txt', 'r') as f:
        for word in f:
            word = word.strip()
            stop_words.add(word)
    return stop_words

'''
titles =
[
    "The Neatest Little Guide to Stock Market Investing",
    "Investing For Dummies, 4th Edition",
    "The Little Book of Common Sense Investing: The Only Way to Guarantee Your Fair Share of Stock Market Returns",
    "The Little Book of Value Investing",
    "Value Investing: From Graham to Buffett and Beyond",
    "Rich Dad's Guide to Investing: What the Rich Invest in, That the Poor and the Middle Class Do Not!",
    "Investing in Real Estate, 5th Edition",
    "Stock Investing For Dummies",
    "Rich Dad's Advisors: The ABC's of Real Estate Investing: The Secrets of Finding Hidden Profits Most Investors Miss"
    ]
#stopwords = ['and','edition','for','in','little','of','the','to']
'''
ignorechars = '''!"#$%&()*+,-./:;<=>?@[\]^_`{|}~'''


class LSA(object):

    def __init__(self, stopwords, ignorechars):
        self.stopwords = stopwords
        self.ignorechars = ignorechars
        # dict[word] = [documents it appears in]
        self.wdict = {}
        self.dcount = 0
        # doc_dict[doc_name] = column
        self.doc_dict = {}

    def parse_document(self, doc_name, doc):
        words = doc.split();
        for w in words:
            w = unicodedata.normalize('NFC', w).encode('ascii', 'ignore')
            w = w.lower().translate(None, self.ignorechars)
            #w = w.lower()
            if w in self.stopwords:
                continue
            elif w in self.wdict:
                self.wdict[w].append(self.dcount)
            else:
                self.wdict[w] = [self.dcount]
        self.doc_dict[doc_name] = self.dcount
        self.dcount += 1

    def build_matrix(self):
        """
        Create the internal numpy matrix:
        A[word_idx, document_idx]
        """
        self.keys = [k for k in self.wdict.keys() if len(self.wdict[k]) > 1]
        self.keys.sort()
        self.A = zeros([len(self.keys), self.dcount])
        for i, k in enumerate(self.keys):
            for d in self.wdict[k]:
                self.A[i,d] += 1

    def TFIDF(self):
        WordsPerDoc = numpy.sum(self.A, axis=0)
        DocsPerWord = numpy.sum(asarray(self.A > 0, 'i'), axis=1)
        rows, cols = self.A.shape
        for i in range(rows):
            for j in range(cols):
                self.A[i,j] = (self.A[i,j] / WordsPerDoc[j]) * log(float(cols) / DocsPerWord[i])

    def generate_cosine_matrix(self):
        pass
                
    def printA(self):
        print self.A

    def get_column(self, name):
        """
        Print the row corresponding to
        the given restaurant
        """
        # Get the column for the document
        column = self.doc_dict[name]
        return self.A[:,column]


def main():

    # Create a lsa
    stopwords = get_stopwords()
    lsa = LSA(stopwords, ignorechars)

    # Add documents
    db, connection = connect_to_database(table_name="barkov_chain")
    nymag = db['nymag']
    locations = nymag.find({ 'review' : {'$exists':True} },
                           limit = 100)
    test_location = None
    for location in locations:
        test_location = location
        lsa.parse_document(location['name'], location['review'])

    lsa.build_matrix()
    lsa.TFIDF()
    lsa.printA()
    name = test_location['name']
    review = test_location['review']
    print name, review
    column = lsa.get_column(name)
    important_words = []
    for word, val in zip(lsa.keys, column):
        if val == 0: continue
        important_words.append((word, val))
    important_words.sort(key=lambda x: x[1], reverse=True)
    for word, val in important_words:
        print word, val
    #lsa.print_restaurant(location_name)
    return


if __name__ =="__main__":
    main()
