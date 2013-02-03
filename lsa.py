
from __future__ import division

import json
import itertools
import argparse
import numpy
from numpy import zeros, asarray
from scipy.linalg import svd
import unicodedata

import nltk
from nltk.corpus import wordnet

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

    def __init__(self, stopwords=None, ignorechars=None,
                 size=None, tf=False, idf=False):
        self.stopwords = stopwords
        self.ignorechars = ignorechars
        self.tf = tf
        self.idf = idf
        self.size = size
        # dict[word] = [documents it appears in]
        self.wdict = {}
        self.dcount = 0
        # doc_dict[doc_name] = column
        self.doc_dict = {}

    def parse_document(self, doc_name, doc):

        #doc = doc.decode("utf8")
        #words = doc.split()
        words = nltk.word_tokenize(doc)
        #words_in_doc = []
        for w in words:
            w = unicodedata.normalize('NFC', w).encode('ascii', 'ignore')
            w = w.lower().translate(None, self.ignorechars)

            # Skip invalid words
            if w == '': 
                continue
            if w in self.stopwords:
                continue
            if not wordnet.synsets(w):
                print "%s is not a valid word" % w
                continue
            has_number = False
            for num in [str(num) for num in range(10)]:
                if num in w:
                    print "Removing word %s with number: %s" % (w, num)
                    has_number = True
                    break
            if has_number:
                continue

            # Add to wdict
            # wdict[word] is a list of document id numbers
            # that contain the word 'word'
            # Document id numbers can appear multiple times,
            # indicating multiple times a word appears in a doc
            if w in self.wdict:
                self.wdict[w].append(self.dcount)
            else:
                self.wdict[w] = [self.dcount]
            #words_in_doc.append(w)

        # Add this document to the name map
        self.doc_dict[doc_name] = self.dcount
        # Increase the number of documents viewed
        self.dcount += 1


    def build_matrix(self):
        """
        Create the internal numpy matrix:
        A[word_idx, document_idx]
        """

        print "Building Matrix"
        # Get keys that appear in more than 1 document
        self.keys = [k for k in self.wdict.keys() if len(self.wdict[k]) > 1]
        self.keys.sort()

        # Loop over words.
        # For each word, get the document it appears in, 
        # increase that count in the matrix.
        # Recall, words can appear in the same document 
        # multiple times, so they will be in wdict[k] multiple times
        self.A = zeros([len(self.keys), self.dcount])
        for i, k in enumerate(self.keys):
            for d in self.wdict[k]:
                self.A[i,d] += 1

        print "Successfully built lsa matrix:"
        print "words: %s" % len(self.keys)
        print "Documents: %s" % len(self.doc_dict)
        print "Shape: ", self.A.shape 


    def tf_idf(self):
        """
        Implement Term Frequency, Inverse Document Frequency
        Include logarithmic suppression
        """
        if not self.tf and not self.idf:
            return

        print "TF_IDF"
        WordsPerDoc = numpy.sum(self.A, axis=0)
        DocsPerWord = numpy.sum(asarray(self.A > 0, 'i'), axis=1)
        word_list = []
        rows, cols = self.A.shape
        for i in range(rows):
            for j in range(cols):
                val = self.A[i, j]
                if self.tf: val /= WordsPerDoc[j]
                if self.idf: val *= log(float(cols) / DocsPerWord[i])
                self.A[i, j] = val
        for i in range(rows):
            word = self.keys[i]
            docs_per_word = DocsPerWord[i]
            word_list.append((word, docs_per_word))
                #self.A[i,j] = (self.A[i,j] / WordsPerDoc[j]) * log(float(cols) / DocsPerWord[i])
                
        with open('tf_idf.txt', 'wb') as fp:
            #for word, docs_per_word in zip(self.keys, DocsPerWord):
            #    tfidf = log(float(cols) / docs_per_word)
            #    word_list.append((word, docs_per_word, tfidf))
            word_list.sort(key=lambda x: x[1], reverse=True)
            for word, docs_per_word in word_list:
                line = "%s %s \n" % (word, docs_per_word)
                fp.write(line)


    def run_svd(self):
        """
        Run the Singular Value Decomposition
        """
        print "Running SVD"
        self.U, self.S, self.Vt = svd(self.A, full_matrices=False)


    def reduce(self):
        """
        Reduce the size of the svd matrices 
        
        Initial shape:
        (word, document) = 
             (word, dim) * (dim, dim) * (dim, document)

        """
        size = self.size
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

        
    def _get_document_vector(self, name):
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
        try:
            column = self.doc_dict[name]
        except KeyError:
            print "Venue %s not found in svd corpus" % name
            raise
        return self.Vt[:,column]


    def user_cosine(self, user_vec, doc):
        """
        Get the cosine between the user's current state
        and the proposed document.
        """
        
        doc_vec = self.get_svd_document_vector(doc)
        doc_vec = doc_vec[:len(user_vec)]
        print "Getting Cosine: ",
        for a, b in zip(user_vec, doc_vec):
            print "(%s, %s)" % (a, b),
        return numpy.dot(user_vec, doc_vec)

    
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

        print "Saving: ", self

        # Save an info text file about the lsa
        with open('lsa_info.txt', 'wb') as fp:
            fp.write(str(self))
            words_per_row = 10
            fp.write("\n\nKeys:\n")
            for i, key in enumerate(self.keys):
                if i % words_per_row == 0:
                    fp.write('\n')
                fp.write("%s " % key)
            fp.write("\n\nStop Words:\n")
            for i, word in enumerate(self.stopwords):
                if i % words_per_row == 0:
                    fp.write('\n')
                fp.write("%s " % word)
            fp.write("\n\nSingular Values:\n")
            for val in self.S:
                fp.write("%s \n" % val)

        # Save the matrices
        numpy.save("lsa_A.npy", self.A)
        numpy.save("lsa_U.npy", self.U)
        numpy.save("lsa_S.npy", self.S)
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


    def __repr__(self):
        """
        Implement the string representation
        """
        lsa_str = "LSA Object"
        if self.tf: lsa_str += ", scaled by term frequency (tf)"
        if self.idf: lsa_str += ", scaled by inverse document frequency (idf)"
        lsa_str += '\n'
        lsa_str += "Num words: %s \n" % len(self.keys)
        lsa_str += "Num documents: %s \n" % len(self.doc_dict)
        lsa_str += "Num Singular Values: %s \n" % self.size
        lsa_str += "A %s %s kb \n" % (self.A.shape, self.A.nbytes/1000)
        lsa_str += "U %s %s kb \n" % (self.U.shape, self.U.nbytes/1000)
        lsa_str += "S %s %s kb \n" % (self.S.shape, self.S.nbytes/1000)
        lsa_str += "Vt %s %s kb \n" % (self.Vt.shape, self.Vt.nbytes/1000)
        return lsa_str


def main():

    parser = argparse.ArgumentParser(description='Scrape data from NYMag.')
    parser.add_argument('--create', '-c', dest='create', action="store_true", default=False, 
                        help='Create and save the lsa object')
    parser.add_argument('--test', '-t', dest='test', action="store_true", default=False, 
                        help='Test the lsa')
    parser.add_argument('--limit', '-l', dest='limit', type=int, default=None, 
                        help='Maximum number of venues to use in sva matrix (default is all)')
    parser.add_argument('--size', '-s', dest='size', type=int, default=None, 
                        help='Number of Support Vector dimensions to use')
    parser.add_argument('--tf', dest='tf', action="store_true", default=False, 
                        help='Scale values by term frequency')
    parser.add_argument('--idf', dest='idf', action="store_true", default=False, 
                        help='Scale values by inverse document frequency')

    args = parser.parse_args()

    ignorechars = '''!"#$%&()*+,-./:;<=>?@[\]^_`{|}~'''
    stopwords = get_stopwords()
    lsa = LSA(stopwords, ignorechars, size=args.size,
              tf=args.tf, idf=args.idf )

    if args.create:

        # Add documents
        db, connection = connect_to_database(table_name="barkov_chain")
        bars = db['bars']
        if args.limit:
            locations = bars.find({ 'nymag.review' : {'$ne':None}, 
                                    'foursquare.tips' : {'$exists':True}, 
                                    'foursquare.tips' : {'$ne':None} 
                                    }).limit(args.limit)
        else:
            locations = bars.find({ 'nymag.review' : {'$ne':None},
                                    'foursquare.tips' : {'$exists':True}, 
                                    'foursquare.tips' : {'$ne':None}
                                    })

        for location in locations:
            nymag = location['nymag']
            name = nymag['name']
            # Get the text for the semantic processing
            description = nymag['review']
            fsq_tips = location['foursquare']['tips']
            description.join([tip['text'] for tip in fsq_tips])
            lsa.parse_document(name, description)

        lsa.build_matrix()
        numpy.set_printoptions(threshold='nan')
        #lsa.tf_idf(tf=True, idf=False)
        lsa.tf_idf()
        lsa.run_svd()
        lsa.check_consistency()
        lsa.reduce()
        #if args.size != None:
        #    lsa.reduce(args.size)
        lsa.save()

    if args.test:

        lsa.load()
        lsa.reduce()
        test_bars = ["Bantam", "1 Oak", "Amity Hall", "Ainsworth Park", "B Bar & Grill", "Ajna Bar",
                     "Amsterdam Ale House", "2nd Floor on Clinton","The Griffin", "Artifakt Bar", 
                     "Forty Eight Lounge", "129", "Bar Seine", "Bar d'Eau", "Blind Tiger Ale House",
                     "Apoth\u00e9ke", "Bill\u2019s Place","Enoteca I Trulli","Bar Baresco",
                     "Glass Bar", "Lovers of Today", "Guilty Goose", "Japas 27", "East End Bar & Grill", 
                     "Experimental Cocktail Club", "Diva Restaurant and Bar", "Blackbird", 
                     "The Lounge at Dixon Place", "The Beatrice Inn", "Josie Wood's Pub", 
                     "Carriage House","Henrietta Hudson", "Failte Irish Whiskey Bar", "A60", "Celsius",
                     "The Lobby Bar at the Ace Hotel", "Above 6", "Great Hall Balcony Bar", "32 Karaoke",
                     "BB&R; (Blonde, Brunette and a Redhead)", "Beekman Beer Garden Beach Club",
                     "116", "McAnn's on 46th", "Bill's Food & Drink"]

        cosine_list = []
        for (barA, barB) in itertools.combinations(test_bars, 2):
            if barA in lsa.doc_dict and barB in lsa.doc_dict:
                overlap = lsa.cosine(barA, barB, size=20)
                cosine_list.append((barA, barB, overlap))
        cosine_list.sort(key=lambda x: x[2], reverse=True)
        for barA, barB, overlap in itertools.chain(cosine_list[0:20], cosine_list[-21:-1]):
            print "Overlap is %s between %s and %s" % (overlap, barA, barB)

    return


if __name__ =="__main__":
    main()
