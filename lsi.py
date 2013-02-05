
from nymag_scrape import connect_to_database
from gensim.models.lsimodel import LsiModel
from gensim import corpora, models, similarities

import logging

import nltk
from nltk.corpus import wordnet
import unicodedata

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
        if w == '': 
            continue
        if w in stopwords:
            continue
        if not wordnet.synsets(w):
            continue
        has_number = False
        for num in [str(num) for num in range(10)]:
            if num in w:
                has_number = True
                break
        if has_number:
            continue

        tokens.append(w)
        
    return tokens


def create_texts(doc_iterator):

    texts = []

    for doc in doc_iterator:
        tokens = tokenize_document(doc)
        texts.append(tokens)

    # Get all tokens in our corpus
    # and remove words that appear only once
    all_tokens = sum(texts, [])
    tokens_once = set(word for word in set(all_tokens) if all_tokens.count(word) == 1)
    texts = [ [word for word in text if word not in tokens_once]
             for text in texts]

    return texts


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
    

def main():

    logging.basicConfig(format='%(asctime)s : %(levelname)s : %(message)s', level=logging.INFO)
    
    # Add documents
    db, connection = connect_to_database(table_name="barkov_chain")
    bars = db['bars']
    num_bars = 50
    locations = bars.find({ 'nymag.review' : {'$ne':None}, 
                            'foursquare.tips' : {'$exists':True}, 
                            'foursquare.tips' : {'$ne':None} 
                            }).limit(num_bars)

    ignorechars = '''!"#$%&()*+,-./:;<=>?@[\]^_`{|}~'''
    stopwords = get_stopwords()

    texts = []
    
    for location in locations:
        nymag = location['nymag']
        name = nymag['name']
        description = nymag['review']
        fsq_tips = location['foursquare']['tips']
        description.join([tip['text'] for tip in fsq_tips])
        tokens = tokenize_document(description, stopwords, ignorechars)
        texts.append(tokens)

    # Do some cleaning
    texts = remove_words_appearing_once(texts)

    # Create the dictionary
    dictionary = corpora.Dictionary(texts)
    dictionary.save('lsi.dict')

    corpus = [dictionary.doc2bow(text) for text in texts]
    corpora.MmCorpus.serialize('lsi.corpus.mm', corpus) 

    # Term Frequency, Inverse Document Frequency
    tfidf = models.TfidfModel(corpus) 
    corpus_tfidf = tfidf[corpus]

    # Create the model
    lsi = models.LsiModel(corpus_tfidf, id2word=dictionary, num_topics=5) 
    corpus_lsi = lsi[corpus_tfidf]
    #lsi.print_topics(2)

    lsi.save('model.lsi')

    index = similarities.MatrixSimilarity(lsi[corpus])

    test_vector = lsi[corpus[0]]

    sims = index[test_vector]
    sims = sorted(enumerate(sims), key=lambda item: -item[1])
    print sims
    return

    sims = sorted(enumerate(sims), key=lambda item: -item[1])
    print sims
    
    #model = ldamodel.LdaModel(bow_corpus, id2word=dictionary, num_topics=100)

    return

    tfidf = models.TfidfModel(corpus)

    index = similarities.SparseMatrixSimilarity(tfidf[corpus], num_features=12)

    sims = index[tfidf[vec]]



if __name__ == "__main__":
    main()
