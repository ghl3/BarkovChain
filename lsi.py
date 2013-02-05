

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


def load_lsi():
    """
    Load the saved-on-disk lsi
    object and return it.
    """
    lsi = models.LsiModel.load('model.lsi')
    corpus = corpora.MmCorpus('lsi.corpus.mm')
    corpus_tfidf = corpora.MmCorpus('lsi.corpus_tfidf.mm')
    dictionary = corpora.Dictionary.load('lsi.dict')

    return (lsi, corpus, corpus_tfidf, dictionary)
    

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
    bar_map = {}

    print "Fetching texts from database and tokenizing"
    for idx, location in enumerate(locations):
        bar_map[idx] = location['nymag']['name']
        text = create_string_from_database(location)
        tokens = tokenize_document(text, stopwords, ignorechars)
        texts.append(tokens)

    # Do some cleaning
    print "Cleaning texts"
    texts = remove_words_appearing_once(texts)

    # Create and save the dictionary
    print "Creating dictionary"
    dictionary = corpora.Dictionary(texts)
    dictionary.save('lsi.dict')

    # Create and save the corpus
    print "Creating Corpus matrix"
    corpus = [dictionary.doc2bow(text) for text in texts]
    corpora.MmCorpus.serialize('lsi.corpus.mm', corpus) 

    # Term Frequency, Inverse Document Frequency
    print "Applying TFIDF"
    tfidf = models.TfidfModel(corpus) 
    corpus_tfidf = tfidf[corpus]
    corpora.MmCorpus.serialize('lsi.corpus_tfidf.mm', corpus_tfidf) 

    # Create the model
    print "Creating LSI with %s topics" % num_topics
    lsi = models.LsiModel(corpus_tfidf, id2word=dictionary, num_topics=num_topics) 
    lsi.save('model.lsi')
    
    # Save some additional info
    with open('lsi_bar_map.json', 'wb') as fp:
        json.dump(bar_map, fp)

    with open('lsi_info.txt', 'wb') as fp:
        ts = time.time()
        st = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
        fp.write("LSI Model %s\n" % st)
        info = "Number of Docs: %s Number of Topics: %s\n" % (len(corpus), num_topics)
        fp.write(info)
        


def test_lsi():

    lsi, corpus, corpus_tfidf, dictionary = load_lsi()

    # Now that everything is generated and saved,
    # we can begin using the lsi
    corpus_lsi = lsi[corpus_tfidf]
    lsi.print_topics(10)
    
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
        print cosine, 
        print '{', [word for word in words if word in test_words], '}',
        print words
        print ''

    return


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
        test_lsi()

    return


if __name__ == "__main__":
    main()
