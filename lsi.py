
from __future__ import division

import logging
import argparse
import itertools

import time
import datetime
import json
import nltk
from nltk.corpus import wordnet
import unicodedata

from nymag_scrape import connect_to_database

from gensim.models.lsimodel import LsiModel
from gensim import corpora, models, similarities
from math import sqrt

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


def tokenize_document(doc, stopwords, ignorechars):
    """
    Take an input string, tokenize it,
    clean the token, and return a list
    of key words
    """
    
    tokens = []

    words = nltk.word_tokenize(doc)
    for w in words:
        w = unicodedata.normalize('NFC', w).encode('ascii', 'ignore')
        w = w.lower().translate(None, ignorechars)

        # Skip invalid words
        if w == '': continue
        if w in stopwords: continue
        if not wordnet.synsets(w): continue
        has_number = False
        for num in [str(num) for num in range(10)]:
            if num in w:
                has_number = True
                break
        if has_number: continue

        tokens.append(w)
        
    return tokens


def remove_words_appearing_once(texts):
    """
    Return a new text where words appearing
    only once have been removed
    """
    all_tokens = sum(texts, [])
    tokens_once = set(word for word in set(all_tokens) if all_tokens.count(word) == 1)
    texts = [ [word for word in text if word not in tokens_once]
             for text in texts]
    return texts


def create_string_from_database(db_entry):
    """
    Take a location database entry and
    convert it into a single string, 
    including reviews and tips
    """

    nymag = db_entry['nymag']
    name = nymag['name']
    text = nymag['review']
    fsq_tips = db_entry['foursquare']['tips']
    text.join([tip['text'] for tip in fsq_tips])

    return text

def create_lsi(db, num_topics=10, num_bars=None):
    """
    Create and save a lsi object
    using data in the database.
    Save this object, along with the
    dictionary and the corpus, to disk
    """

    bars = db['bars']

    if num_bars == None:
        locations = bars.find({ 'nymag.review' : {'$ne':None}, 
                                'foursquare.tips' : {'$exists':True}, 
                                'foursquare.tips' : {'$ne':None} 
                                })
    else:
        locations = bars.find({ 'nymag.review' : {'$ne':None}, 
                                'foursquare.tips' : {'$exists':True}, 
                                'foursquare.tips' : {'$ne':None} 
                                }).limit(num_bars)

    ignorechars = '''!"#$%&()*+,-./:;<=>?@[\]^_`{|}~'''
    stopwords = get_stopwords()

    texts = []
    bar_idx_map = {}
    idx_bar_map = {}

    save_directory = "data/"

    print "Fetching texts from database and tokenizing"
    for idx, location in enumerate(locations):
        bar_name = location['nymag']['name']
        bar_idx_map[bar_name] = idx
        idx_bar_map[idx] = bar_name
        text = create_string_from_database(location)
        tokens = tokenize_document(text, stopwords, ignorechars)
        texts.append(tokens)

    # Do some cleaning
    print "Cleaning texts"
    texts = remove_words_appearing_once(texts)

    # Create and save the dictionary
    print "Creating dictionary"
    dictionary = corpora.Dictionary(texts)
    dictionary.save(save_directory + 'lsi.dict')

    # Create and save the corpus
    print "Creating Corpus matrix"
    corpus = [dictionary.doc2bow(text) for text in texts]
    corpora.MmCorpus.serialize(save_directory + 'corpus.mm', corpus) 

    # Term Frequency, Inverse Document Frequency
    print "Applying TFIDF"
    tfidf = models.TfidfModel(corpus) 
    tfidf.save(save_directory + "tfidf.model")

    # Map TFIDF on the corpus
    print "Mapping TFIDF on corpus"
    corpus_tfidf = tfidf[corpus]
    corpora.MmCorpus.serialize(save_directory + 'corpus_tfidf.mm', corpus_tfidf) 

    # Create the LSI
    print "Creating LSI with %s topics" % num_topics
    lsi = models.LsiModel(corpus_tfidf, id2word=dictionary, num_topics=num_topics) 
    lsi.save(save_directory + 'lsi.model')

    # Map LSI on the corpus
    corpus_lsi_tfidf = lsi[corpus_tfidf]
    corpora.MmCorpus.serialize(save_directory + 'corpus_lsi_tfidf.mm', corpus_lsi_tfidf)

    # Create the index
    #index = similarities.MatrixSimilarity(lsi[corpus_tfidf])
    index = similarities.MatrixSimilarity(corpus_lsi_tfidf)
    index.save(save_directory + 'lsi_tfidf.index')
    
    # Save some additional info
    with open(save_directory + 'lsi_bar_idx_map.json', 'wb') as fp:
        json.dump(bar_idx_map, fp)

    with open(save_directory + 'lsi_idx_bar_map.json', 'wb') as fp:
        json.dump(idx_bar_map, fp)

    with open(save_directory + 'lsi_info.txt', 'wb') as fp:
        ts = time.time()
        st = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
        fp.write("LSI Model %s\n" % st)
        info = "Number of Docs: %s Number of Topics: %s\n" % (len(corpus), num_topics)
        fp.write(info)

        # Print Stop Words
        words_per_row = 10
        fp.write("\n\nStop Words:\n")
        for i, word in enumerate(stopwords):
            if i % words_per_row == 0:
                fp.write('\n')
            fp.write("%s " % word)


def load_lsi(directory=''):
    """
    Load the saved-on-disk lsi
    object and return it.
    """

    if directory != '' and directory[-1] != '/':
        directory = directory + '/'
    
    dictionary = corpora.Dictionary.load(directory + 'lsi.dict')
    corpus = corpora.MmCorpus(directory + 'corpus.mm')
    tfidf = models.TfidfModel.load(directory + 'tfidf.model')
    lsi = models.LsiModel.load(directory + 'lsi.model')
    corpus_lsi_tfidf = corpora.MmCorpus(directory + 'corpus_lsi_tfidf.mm')
    index = similarities.MatrixSimilarity.load(directory + 'lsi_tfidf.index')

    #corpus = corpora.MmCorpus('lsi.corpus.mm')
    #corpus_tfidf = 

    with open(directory + 'lsi_bar_idx_map.json', 'rb') as fp:
        bar_idx_map = json.load(fp)

    with open(directory + 'lsi_idx_bar_map.json', 'rb') as fp:
        idx_bar_map = json.load(fp)

    return (dictionary, lsi, tfidf, corpus, corpus_lsi_tfidf, 
            index, bar_idx_map, idx_bar_map)
    

def test_lsi(db):

    # Grab random locations
    bars = db['bars']
    bar_names = []
    locations = bars.find({ 'nymag.review' : {'$ne':None}, 
                            'foursquare.tips' : {'$exists':True}, 
                            'foursquare.tips' : {'$ne':None} 
                            }).limit(10)

    for location in locations:
        bar_names.append(location['nymag']['name'])

    # Create a corpus from this
    dictionary, lsi, tfidf, corpus, corpus_lsi_tfidf, \
        index, bar_idx_map, idx_bar_map = load_lsi()

    #lsi, corpus, corpus_tfidf, dictionary, \
    #    index, bar_idx_map, idx_bar_map = load_lsi()

    #lsi, corpus, corpus_tfidf, dictionary, bar_idx_map, idx_bar_map = load_lsi()
    lsi.print_topics(10)

    # Get the tfidf vectors
    #corpus_tfidf = [corpus_tfidf[bar_idx_map[name]] for name in bar_names ]
    #print corpus_tfidf

    # And transform to the lsi space
    #corpus_lsi = lsi[corpus_tfidf]
    #print corpus_lsi

    # Create a matching function
    #index = similarities.MatrixSimilarity(corpus_lsi)

    #test_vector = lsi[corpus_tfidf[0]]
    test_vector = corpus_lsi_tfidf[0]
    test_words = [dictionary[word[0]] for word in test_vector]    
    sims = index[test_vector]
    sims = sorted(enumerate(sims), key=lambda item: -item[1])

    print "Comparing to: "
    print test_words
    print test_vector
    print ''

    for doc_idx, cosine in itertools.chain(sims[0:10], sims[-10:-1]):
        words = [dictionary[pair[0]] for pair in corpus[doc_idx]]
        print cosine, 
        print '{', [word for word in words if word in test_words], '}',
        print words
        print ''

    return

    # Create the similarity index
    index = similarities.MatrixSimilarity(lsi[corpus])

    # Test the similarities
    test_vector = lsi[corpus[0]]
    test_words = [dictionary[word[0]] for word in test_vector]
    sims = index[test_vector]
    sims = sorted(enumerate(sims), key=lambda item: -item[1])

    print test_vector
    print "Comparing to: "
    print test_words
    print ''

    for doc_idx, cosine in itertools.chain(sims[0:10], sims[-10:-1]):
        words = [dictionary[pair[0]] for pair in corpus[doc_idx]]
        
        my_cosine = numpy.dot(self.index, query.T).T 
        print cosine, 
        print '{', [word for word in words if word in test_words], '}',
        print words
        print ''

    return


def cosine(A, B):
    """
    Return the cosine between two lsi rows.
    The inputs are vectors in the form:

    [ (idx, val), (idx, val), ... ]
    """
    magA = sqrt(sum([x[1]*y[1] for (x, y) in zip(A, A)]))
    magB = sqrt(sum([x[1]*y[1] for (x, y) in zip(B, B)]))
    dotP = sum([x[1]*y[1] for (x, y) in zip(A, B)])
    return dotP / (magA*magB)


def important_words(lsi, docA, docB):
    """
    Return an ordered list of 
    important words for a document
    comaprison.
    """

    # Get the word mapping
    # [ [(0.10818501434348921, 'room'), (0.1065805102429373, 'space'), ... ],
    #    ...
    #   [ ...,  (-0.089040641678911847, 'sports'), (-0.088569259768822226, 'ginger')] ]
    topic_list = lsi.show_topics(formatted=False)
    
    # Calculate the element-by-element overlap
    overlap = [valA[1]*valB[1] for (valA, valB) in zip(docA, docB)]

    # Reverse sort it
    # overlap = sort(enumerate(overlap), key=lambda x: x[1], reverse=True)

    # Create a dictionary to hold the word values
    word_val_dict = {}
    for topic, topic_weight in zip(topic_list, overlap):
        # Topic = [(0.10818501434348921, 'room'), (0.1065805102429373, 'space'), ... ]
        for word_weight, word in topic:
            if word not in word_val_dict:
                word_val_dict[word] = word_weight * topic_weight
            else:
                word_val_dict[word] += word_weight * topic_weight

    # Turn the dict into a (reverse) sorted list of word, strenght pairs
    return sorted(list(word_val_dict.iteritems()), key=lambda x: x[1], reverse=True)


def main():

    parser = argparse.ArgumentParser(description='Scrape data from NYMag.')
    parser.add_argument('--create', '-c', dest='create', action="store_true", default=False, 
                        help='Create and save the lsa object')
    parser.add_argument('--test', '-t', dest='test', action="store_true", default=False, 
                        help='Test the lsa')

    parser.add_argument('--limit', '-l', dest='limit', type=int, default=None, 
                        help='Maximum number of venues to use in sva matrix (default is all)')
    parser.add_argument('--size', '-s', dest='size', type=int, default=10, 
                        help='Number of Support Vector dimensions to use')

    args = parser.parse_args()

    logging.basicConfig(format='%(asctime)s : %(levelname)s : %(message)s', level=logging.INFO)
    
    # Add documents
    db, connection = connect_to_database(table_name="barkov_chain")

    if args.create:
        create_lsi(db, args.size, args.limit)

    if args.test:
        test_lsi(db)

    return


if __name__ == "__main__":
    main()
