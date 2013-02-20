
from __future__ import division

import logging
import argparse
import itertools

import re
import time
import datetime
import json
import nltk
from nltk.corpus import wordnet
from nltk.stem.wordnet import WordNetLemmatizer

import unicodedata
from collections import Counter

from nymag_scrape import connect_to_database

from gensim.models.lsimodel import LsiModel
from gensim.models.ldamodel import LdaModel

from gensim import corpora, models, similarities
from math import sqrt, fabs

def get_stopwords():
    """
    Load the collection of stop words
    into memory
    """
    stop_words = set()

    with open('stop-words.txt', 'r') as f:
        for word in f:
            word = word.strip().lower()
            stop_words.add(word)

    with open('first_names.csv', 'r') as f:
        for line in f:
            for word in line.splitlines():
                word = word.strip().lower()
                stop_words.add(word)

    with open('custom-stop-words.txt', 'r') as f:
        for word in f:
            word = word.strip().lower()
            stop_words.add(word)

    return stop_words


def tokenize_document(doc, stopwords, ignorechars):
    """
    Take an input string, tokenize it,
    clean the token, and return a list
    of key words
    """
    
    tokens = []

    # Remove any html tags that may
    # have suck in
    doc = re.sub('<[^>]*>', '', doc)

    lmtzr = WordNetLemmatizer()
    words = nltk.word_tokenize(doc)
    for w in words:
        
        w = unicodedata.normalize('NFC', w).encode('ascii', 'ignore')
        w = w.lower().translate(None, ignorechars)

        # Skip invalid words
        if w == '': continue

        # Check if the original word is a stop words, 
        # then lemmatize, then check again
        if w in stopwords: continue
        w = lmtzr.lemmatize(w)
        if w in stopwords: continue

        # Ensure it's a real word
        if not wordnet.synsets(w): continue

        # Remove numerics
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
    tip_str = ' '.join([tip['text'] for tip in fsq_tips])

    text = text + " " + tip_str

    categories = nymag['categories']
    if categories != None:
        category_str = ' '.join(categories)
        text = text + " " + category_str
        
    return text


def create_models(db, lsi_num_topics=10, lda_num_topics=5, num_bars=None):
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

    save_directory = "assets/"

    print "Fetching texts from database and tokenizing"
    for idx, location in enumerate(locations):
        bar_name = location['nymag']['name']
        bar_idx_map[bar_name] = idx
        idx_bar_map[int(idx)] = bar_name
        text = create_string_from_database(location)
        tokens = tokenize_document(text, stopwords, ignorechars)
        texts.append(tokens)

    # Do some cleaning
    print "Cleaning texts"
    texts = remove_words_appearing_once(texts)

    # Create the counter
    word_counts = Counter()
    for text in texts: 
        word_counts.update(text)       

    # Create and save the dictionary
    print "Creating dictionary"
    dictionary = corpora.Dictionary(texts)
    dictionary.save(save_directory + 'keywords.dict')

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
    print "Creating LSI with %s topics" % lsi_num_topics
    lsi = models.LsiModel(corpus_tfidf, id2word=dictionary, num_topics=lsi_num_topics) 
    lsi.save(save_directory + 'lsi.model')

    # Map LSI on the corpus
    corpus_lsi_tfidf = lsi[corpus_tfidf]
    corpora.MmCorpus.serialize(save_directory + 'corpus_lsi_tfidf.mm', corpus_lsi_tfidf)

    # Create the index
    #index = similarities.MatrixSimilarity(lsi[corpus_tfidf])
    index = similarities.MatrixSimilarity(corpus_lsi_tfidf)
    index.save(save_directory + 'lsi_tfidf.index')

    # Create the LDA (on the raw corpus)
    print "Creating LDA with %s topics" % lda_num_topics
    lda = LdaModel(corpus, num_topics=lda_num_topics, id2word=dictionary, 
                   update_every=0, passes=30)
    #lda.show_topics(10, 20, formatted=False)
    lda.save(save_directory + 'lda.model')

    # Create the lda corpus
    corpus_lda = lda[corpus]
    corpora.MmCorpus.serialize(save_directory + 'corpus_lda.mm', corpus_lda)

    # Save some additional info
    with open(save_directory + 'bar_idx_map.json', 'wb') as fp:
        json.dump(bar_idx_map, fp)

    with open(save_directory + 'idx_bar_map.json', 'wb') as fp:
        json.dump(idx_bar_map, fp)

    with open(save_directory + 'model_info.txt', 'wb') as fp:
        ts = time.time()
        st = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
        fp.write("LSI Model %s\n" % st)
        info = "Number of Docs: %s\n" % len(corpus)
        info += "Number of key words: %s\n" % len(dictionary)
        info += "Number of LSI Topics: %s\n" % lsi_num_topics
        info += "Number of LDA Topics: %s\n" % lda_num_topics
        fp.write(info)

        # Print Stop Words
        words_per_row = 10
        fp.write("\n\nStop Words:\n")
        for i, word in enumerate(stopwords):
            if i % words_per_row == 0:
                fp.write('\n')
            fp.write("%s " % word)

        # Print Corpus
        fp.write("\n\nWords Encountered:\n")
        for word, count in word_counts.most_common():
            idx = dictionary.token2id[word]
            line = "%s (index=%s) freq: %s \n" % (word, idx, count)
            fp.write(line)


def load_corpus(directory='assets/'):

    if directory != '' and directory[-1] != '/':
        directory = directory + '/'

    dictionary = corpora.Dictionary.load(directory + 'keywords.dict')
    corpus = corpora.MmCorpus(directory + 'corpus.mm')
    tfidf = models.TfidfModel.load(directory + 'tfidf.model')

    with open(directory + 'bar_idx_map.json', 'rb') as fp:
        bar_idx_map = json.load(fp)

    with open(directory + 'idx_bar_map.json', 'rb') as fp:
        idx_bar_map = json.load(fp)

    return (dictionary, corpus, tfidf,
            bar_idx_map, idx_bar_map)


def load_lsi(directory='assets/'):
    """
    Load the lsi model, corpus matrix, and index
    """

    if directory != '' and directory[-1] != '/':
        directory = directory + '/'
    
    lsi = models.LsiModel.load(directory + 'lsi.model')
    corpus_lsi_tfidf = corpora.MmCorpus(directory + 'corpus_lsi_tfidf.mm')
    index = similarities.MatrixSimilarity.load(directory + 'lsi_tfidf.index')

    return (lsi, corpus_lsi_tfidf, index)
    

def load_lda(directory='assets/'):
    """
    Load the lda model and corpus matrix
    """

    if directory != '' and directory[-1] != '/':
        directory = directory + '/'
    
    lda = models.LsiModel.load(directory + 'lda.model')
    corpus_lda = corpora.MmCorpus(directory + 'corpus_lda.mm')

    return (lda, corpus_lda)


def test_lsi(db):
    """
    Run a test of lsi
    """

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
    dictionary, corpus, tfidf, bar_idx_map, idx_bar_map = load_corpus()
    lsi, corpus_lsi_tfidf, index = load_lsi()

    lsi.print_topics(10)

    # Run the tests
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


def test_lda(db):
    """
    Test the LDA functionality
    """

    # Grab random locations
    bars = db['bars']
    bar_names = []
    locations = bars.find({ 'nymag.review' : {'$ne':None}, 
                            'foursquare.tips' : {'$exists':True}, 
                            'foursquare.tips' : {'$ne':None} 
                            }).limit(10)

    for location in locations:
        bar_names.append(location['nymag']['name'])

    dictionary, corpus, tfidf, bar_idx_map, idx_bar_map = load_corpus()
    lda, corpus_lda = load_lda()

    print lda.num_topics
    lda.show_topics(-1, 10, True)

    # Print some vector
    for bar_idx, venue in enumerate(corpus_lda):
        bar_name = idx_bar_map[str(bar_idx)]
        total_prob = sum([x[1] for x in venue])
        print bar_name, total_prob, venue
        if bar_idx > 100: break

    # Create a test venue
    test_vector = corpus_lda[0]
    test_words = [dictionary[word[0]] for word in test_vector]    

    index = similarities.MatrixSimilarity(corpus_lda)
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


def covariance(A, B):
    """
    Get the product covariance
    """
    total = 0.0
    for a, b in zip(A, B):
        total += a[1]*b[1]
    return 1.0 - total


def euclidean(A, B):
    """
    Get the product covariance
    """
    total = 0.0
    for a, b in zip(A, B):
        total += (a[1]-b[1])*(a[1]-b[1])
    return sqrt(total)


def kl_divergence(A, B):
    """
    Return the kl-divergence between
    two vectors
    """
    
    kl_div = 0.0
    for (a, b) in zip(A, B):
        if a < 0.000001: continue
        if b < 0.000001: continue
        ratio = a/b
        kl_div += log(ratio)*a
    return kl_div
        

def important_words(lsi, state, num=None):
    """
    Given the lsi and the state, find the most
    important words
    """

    # Get the word mapping
    # [ [(0.10818501434348921, 'room'), (0.1065805102429373, 'space'), ... ],
    #    ...
    #   [ ...,  (-0.089040641678911847, 'sports'), (-0.088569259768822226, 'ginger')] ]
    topic_list = lsi.show_topics(formatted=False)

    word_val_dict = {}
    for topic, topic_weight in zip(topic_list, state):
        # Topic = [(0.10818501434348921, 'room'), (0.1065805102429373, 'space'), ... ]
        for word_weight, word in topic:
            if word not in word_val_dict:
                word_val_dict[word] = fabs(word_weight * topic_weight)
            else:
                word_val_dict[word] += fabs(word_weight * topic_weight)

    # Turn the dict into a (reverse) sorted list of word, strenght pairs
    sorted_list = sorted(list(word_val_dict.iteritems()), key=lambda x: x[1], reverse=True)

    if num:
        return sorted_list[:num]

    return sorted_list


def important_words_relative(lsi, docA, docB):
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


def update_vector(original, latest, closer, beta):
    """
    Update the 'original' vector based on the
    'latest' vector.  Either move the original
    vector closer or further from 'latest' based on
    whether the bool 'closer' is true or not.
    'beta' represents how much the vector should shift.
    """

    delta = beta*(latest - original)

    if closer:
        new = original + beta
    else:
        new = original - beta

    return new


def main():

    parser = argparse.ArgumentParser(description='Scrape data from NYMag.')
    parser.add_argument('--create', '-c', dest='create', action="store_true", default=False, 
                        help='Create and save the lsa object')
    parser.add_argument('--limit', '-l', dest='limit', type=int, default=None, 
                        help='Maximum number of venues to use in sva matrix (default is all)')
    parser.add_argument('--lsi_size', dest='lsi_size', type=int, default=10, 
                        help='Number of LSI Support Vector dimensions to use')
    parser.add_argument('--lda_size', dest='lda_size', type=int, default=10, 
                        help='Number of LDA topics to use')

    parser.add_argument('--test', '-t', dest='test', action="store_true", default=False, 
                        help='Run the tests')

    parser.add_argument('--lsi', dest='lsi', action="store_true", default=False, 
                        help='Test the lsi')

    parser.add_argument('--lda', dest='lda', action="store_true", default=False, 
                        help='Test the lda')

    args = parser.parse_args()

    logging.basicConfig(format='%(asctime)s : %(levelname)s : %(message)s', level=logging.INFO)
    
    # Add documents
    db, connection = connect_to_database(table_name="barkov_chain")

    if args.create:
        create_models(db, lsi_num_topics=args.lsi_size, 
                      lda_num_topics=args.lda_size, 
                      num_bars=args.limit)

    # Run the tests
    if args.test:
        test_lsi(db)
        test_lda(db)
        
    else:
        if args.lsi:
            test_lsi(db)

        if args.lda:
            test_lda(db)

    return


if __name__ == "__main__":
    main()
