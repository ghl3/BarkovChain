
from numpy import zeros
from scipy.linalg import svd
import unicodedata

from nymag_scrape import connect_to_database

def get_stopwords():
    """
    Load the collection of stop words
    into memory
    """
    stop_words = set()
    with open('stop-words.txt', 'r') as f:
        for word in f:
            stop_words.update(word)
    return list(stop_words)

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
        self.wdict = {}
        self.dcount = 0

    def parse_document(self, doc):
        words = doc.split();
        for w in words:
            w = unicodedata.normalize('NFC', w).encode('ascii', 'ignore')
            w = w.lower().translate(None, self.ignorechars)
            if w in self.stopwords:
                continue
            elif w in self.wdict:
                self.wdict[w].append(self.dcount)
            else:
                self.wdict[w] = [self.dcount]
        self.dcount += 1

    def build_matrix(self):
        self.keys = [k for k in self.wdict.keys() if len(self.wdict[k]) > 1]
        self.keys.sort()
        self.A = zeros([len(self.keys), self.dcount])
        for i, k in enumerate(self.keys):
            for d in self.wdict[k]:
                self.A[i,d] += 1

    def printA(self):
        print self.A


def main():

    # Create a lsa
    stopwords = get_stopwords()
    lsa = LSA(stopwords, ignorechars)

    # Add documents
    db, connection = connect_to_database(table_name="barkov_chain")
    nymag = db['nymag']
    locations = nymag.find({ 'review' : {'$exists':True} },
                           limit = 100)
    for location in locations:
        lsa.parse_document(location['review'])

    lsa.build_matrix()
    lsa.printA()
    return


if __name__ =="__main__":
    main()
