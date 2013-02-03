
from __future__ import division

import json
import itertools
import argparse
import numpy
from numpy import zeros, asarray
from scipy.linalg import svd
import unicodedata

from math import log

from nymag_scrape import connect_to_database

# lsa:
# http://www.puffinwarellc.com/index.php/news-and-articles/articles/33.html?showall=1

# svd example:
# http://www.puffinwarellc.com/index.php/news-and-articles/articles/30-singular-value-decomposition-tutorial.html

# plsa:
# http://www.mblondel.org/journal/2010/06/13/lsa-and-plsa-in-python/


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


class LSA(object):

    def __init__(self, stopwords=None, ignorechars=None):
        self.stopwords = stopwords
        self.ignorechars = ignorechars
        # dict[word] = [documents it appears in]
        self.wdict = {}
        self.dcount = 0
        # doc_dict[doc_name] = column
        self.doc_dict = {}
        self.dimensions = 20

    def parse_document(self, doc_name, doc):
        words = doc.split();
        #words_in_doc = []
        for w in words:
            w = unicodedata.normalize('NFC', w).encode('ascii', 'ignore')
            w = w.lower().translate(None, self.ignorechars)
            #w = w.lower()
            if w == '': continue
            if w in self.stopwords:
                continue
            elif w in self.wdict:
                self.wdict[w].append(self.dcount)
            else:
                self.wdict[w] = [self.dcount]
            #words_in_doc.append(w)
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

        print "Successfully built lsa matrix:"
        print "words: %s" % len(self.keys)
        print "Documents: %s" % len(self.doc_dict)
        print "Shape: ", self.A.shape 

    def tf_idf(self):
        WordsPerDoc = numpy.sum(self.A, axis=0)
        DocsPerWord = numpy.sum(asarray(self.A > 0, 'i'), axis=1)
        rows, cols = self.A.shape
        for i in range(rows):
            for j in range(cols):
                self.A[i,j] = (self.A[i,j] / WordsPerDoc[j]) * log(float(cols) / DocsPerWord[i])

    def run_svd(self):
        print "Running SVD"
        self.U, self.S, self.Vt = svd(self.A, full_matrices=False)


    def reduce(self, size):
        """
        Reduce the size of the svd matrices 
        
        Initial shape:
        (word, document) = 
             (word, dim) * (dim, dim) * (dim, document)

        """
        if size == None: return

        print "Initial shape of U: ", self.U.shape
        print "Initial shape of S: ", self.S.shape
        print "Initial shape of Vt: ", self.Vt.shape

        self.U = self.U[:, 0:size]
        self.S = self.S[0:size]
        self.Vt = self.Vt[0:size,:]

        print "Reduced shape of U: ", self.U.shape
        print "Reduced shape of S: ", self.S.shape
        print "Reduced shape of Vt: ", self.Vt.shape

        print "Reduced column for %s" % 'Bantam'
        print self.get_svd_document_vector('Bantam').shape

    def check_consistency(self):
        
        middle = numpy.zeros((len(self.S), len(self.S)))
        for i, point in enumerate(self.S):
            middle[i, i] = point
        prod = numpy.dot(self.U, numpy.dot(middle, self.Vt))
        print prod.shape 
        print prod[0:5, 0:5]
        print self.A.shape
        print self.A[0:5, 0:5]
        print "Matrix is consistent: ", numpy.allclose(self.A, prod, 0.0001)
        
    def top_svd(self, num=None):
        
        # Get the index for sorting:
        print self.S
        sorted_index = [i[0] for i in sorted(enumerate(self.S), key=lambda x: x[1])]
        print sorted_index
        return

        print "S: ", self.S.shape, self.S
        print "S Sorted: ", numpy.sort(self.S)
        return numpy.sort(self.S)[::-1]

    def printA(self):
        print self.A

    def get_document_vector(self, name):
        """
        Print the row corresponding to
        the given restaurant
        """
        # Get the column for the document
        column = self.doc_dict[name]
        return self.A[:,column]

    def get_svd_document_vector(self, name):
        """
        Print the row corresponding to
        the given restaurant
        """
        # Get the column for the document
        column = self.doc_dict[name]
        return self.Vt[:,column]


    def user_cosine(self, user_vec, doc):
        """
        Get the cosine between the user's current state
        and the proposed document.
        """
        
        doc_vec = self.get_svd_document_vector(doc)
        doc_vec = doc_vec[:len(user_vec)]
        return numpy.dot(vecA, vecB)

    
    def update(self, user_vec, doc_vec, accepted=True, beta=0.5):
        """
        This is the all-important update step
        Based on whether a user accepted or rejected a
        proposed 

        This update method is probably wrong, but I'm keeping
        it for now just to move along.
        """
        
        delta = doc_vec - user_vec
        
        if accepted:
            return user_vec + beta*delta
        else:
            return user_vec - beta*delta


    def cosine(self, docA, docB, 
               size=None, reduced=True):
        """
        Get the overlap between the documents

        If 'reduced', use the svd vector
        """
        if reduced:
            vecA = self.get_svd_document_vector(docA)
            vecB = self.get_svd_document_vector(docB)
        else:
            vecA = self.get_document_vector(docA)
            vecB = self.get_document_vector(docB)

        if size != None:
            vecA = vecA[:size]
            vecB = vecB[:size]
            
        return numpy.dot(vecA, vecB)


    def get_word_overlaps(self, docA, docB, num_words=10):
        """
        Return an ordered list containing
        the n most powerful overlap
        words between the two documents.
        """

        vecA = self.get_document_vector(docA)
        vecB = self.get_document_vector(docB)

        keys = self.keys

        for word, valA, valB in zip(keys, vecA, vecB):
            if valA > 0 and valB > 0:
                print word, valA, valB

        return

    
    def save(self):
        """
        Save any items that we need to a file
        """

        # Save the matrices
        print "Saving 'A' %s %s kb " % (self.A.shape, self.A.nbytes/1000)
        numpy.save("lsa_A.npy", self.A)

        print "Saving 'U' %s %s kb" % (self.U.shape, self.U.nbytes/1000)
        numpy.save("lsa_U.npy", self.U)

        print "Saving 'S' %s %s kb" % (self.S.shape, self.S.nbytes/1000)
        numpy.save("lsa_S.npy", self.S)

        print "Saving 'Vt' %s %s kb" % (self.Vt.shape, self.Vt.nbytes/1000)
        numpy.save("lsa_Vt.npy", self.Vt)

        # Save the document dictionary
        with open('doc_dict.json', 'wb') as fp:
            json.dump(self.doc_dict, fp)

        # Save the document dictionary
        with open('keys.json', 'wb') as fp:
            json.dump(self.keys, fp)


    def load(self):
        """
        Load the saved state from a file
        """

        # Load the 'A' matrix
        self.A = numpy.load("lsa_A.npy")
        self.U = numpy.load("lsa_U.npy")
        self.S = numpy.load("lsa_S.npy")
        self.Vt = numpy.load("lsa_Vt.npy")

        with open('doc_dict.json', 'rb') as fp:
            self.doc_dict = json.load(fp)

        with open('keys.json', 'rb') as fp:
            self.keys = json.load(fp)


def main():

    parser = argparse.ArgumentParser(description='Scrape data from NYMag.')
    parser.add_argument('--create', '-c', dest='create', action="store_true", default=False, 
                        help='Create and save the lsa object')
    parser.add_argument('--test', '-t', dest='test', action="store_true", default=False, 
                        help='Test the lsa')
    parser.add_argument('--limit', '-l', dest='limit', type=int, default=None, 
                        help='Maximum number of venues to use in sva matrix (default is all)')
    parser.add_argument('--size', '-s', dest='size', type=int, default=40, 
                        help='Number of Support Vector dimensions to use')
    args = parser.parse_args()

    ignorechars = '''!"#$%&()*+,-./:;<=>?@[\]^_`{|}~'''
    stopwords = get_stopwords()
    lsa = LSA(stopwords, ignorechars)

    if args.create:

        # Add documents
        db, connection = connect_to_database(table_name="barkov_chain")
        nymag = db['bars']
        if args.limit:
            locations = nymag.find({ 'nymag.review' : {'$ne':None} }).limit(args.limit)
        else:
            locations = nymag.find({ 'nymag.review' : {'$ne':None} })

        location_list = []

        for location in locations:
            location = location['nymag']
            name = location['name']
            review = location['review']
            location_list.append( (name, review) )
            lsa.parse_document(location['name'], location['review'])

        lsa.build_matrix()
        lsa.tf_idf()
        lsa.run_svd()
        lsa.check_consistency()
        lsa.reduce(args.size)
        lsa.printA()
        lsa.save()

    if args.test:

        lsa.load()
        test_bars = ["Bantam", "1 Oak", "Amity Hall", "Ainsworth Park", "B Bar & Grill", 
                     "Ajna Bar", "Amsterdam Ale House", "2nd Floor on Clinton"]
        #test_bars = [u"Art Bar", u"The Back Room", u"The Back Fence"]

        for (barA, barB) in itertools.combinations(test_bars, 2):
            overlap = lsa.cosine(barA, barB, size=20)
            #print lsa.get_word_overlaps(barA, barB)
            print "Overlap between %s and %s: %s" % (barA, barB, overlap)

    return

    print lsa.A.shape
    print lsa.U.shape
    print lsa.S.shape
    print lsa.Vt.shape

    print lsa.get_document_vector("Art Bar").shape
    print lsa.get_svd_document_vector("Art Bar").shape

    total = 0
    for valA, valB in zip(lsa.get_svd_document_vector("Art Bar"),
                          lsa.get_svd_document_vector("The Back Room")):
        print valA, valB, valA*valB
        total += valA*valB
    print "Total: ", total
    
    print "Cosine Overlaps:"
    print lsa.cosine(u"The Back Room", u"Art Bar")
    print lsa.cosine(u"The Back Room", u"The Back Room")

    lsa.get_word_overlaps(u"The Back Room", u"Art Bar")

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
