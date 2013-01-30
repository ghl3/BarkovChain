
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

ignorechars = '''!"#$%&()*+,-./:;<=>?@[\]^_`{|}~'''

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

    def tf_idf(self):
        WordsPerDoc = numpy.sum(self.A, axis=0)
        DocsPerWord = numpy.sum(asarray(self.A > 0, 'i'), axis=1)
        rows, cols = self.A.shape
        for i in range(rows):
            for j in range(cols):
                self.A[i,j] = (self.A[i,j] / WordsPerDoc[j]) * log(float(cols) / DocsPerWord[i])

    def run_svd(self):
        self.U, self.S, self.Vt = svd(self.A)

    def generate_cosine_matrix(self):
        pass
                
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

    def get_reduced_document_vector(self, name):
        """
        Print the row corresponding to
        the given restaurant
        """
        # Get the column for the document
        column = self.doc_dict[name]
        return self.Vt[:,column]


    def cosine(self, docA, docB, reduced=True):
        """
        Get the overlap between the documents

        If 'reduced', use the svd vector
        """
        if reduced:
            vecA = self.get_reduced_document_vector(docA)
            vecB = self.get_reduced_document_vector(docB)
        else:
            vecA = self.get_document_vector(docA)
            vecB = self.get_document_vector(docB)
            
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


def main():

    # Create a lsa
    stopwords = get_stopwords()
    lsa = LSA(stopwords, ignorechars)

    # Add documents
    db, connection = connect_to_database(table_name="barkov_chain")
    nymag = db['nymag']
    locations = nymag.find({ 'review' : {'$ne':None} },
                           limit = 300)

    location_list = []

    for location in locations:
        name = location['name']
        review = location['review']
        location_list.append( (name, review) )
        print name, review
        lsa.parse_document(location['name'], location['review'])

    lsa.build_matrix()
    lsa.tf_idf()
    lsa.run_svd()
    lsa.printA()

    #numpy.save("lsa", lsa.A)

    print lsa.A.shape
    print lsa.U.shape
    print lsa.S.shape
    print lsa.Vt.shape



    test_name = u"Art Bar"

    print location_list
    overlaps = []
    for name, review in location_list:
        overlap = lsa.cosine(test_name, name)
        overlaps.append((overlap, name))
    overlaps.sort(key=lambda x: x[0], reverse=True)
    for overlap in overlaps:
        print overlap
    return
        

    print lsa.get_document_vector("Art Bar").shape
    print lsa.get_reduced_document_vector("Art Bar").shape

    total = 0
    for valA, valB in zip(lsa.get_reduced_document_vector("Art Bar"),
                          lsa.get_reduced_document_vector("The Back Room")):
        print valA, valB, valA*valB
        total += valA*valB
    print "Total: ", total
    return
    
    print "Cosine Overlaps:"
    print lsa.cosine(u"The Back Room", u"The Back Fence")
    print lsa.cosine(u"The Back Room", u"Art Bar")
    print lsa.cosine(u"The Back Room", u"The Back Room")
    return

    lsa.get_word_overlaps(u"The Back Room", u"Art Bar")
    return

    return


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
