
import argparse

import re
import time
import urllib2
from bs4 import BeautifulSoup
import nltk

import pymongo
import bson.objectid


# http://nymag.com/srch?t=bar&N=259+69&No=1201&q=Listing%20Type%3ABars&Ns=nyml_sort_name%7C0

def connectToDatabase(table_name="barkov_chain"):
    """ 
    Get a handle on the db object
    """

    try:
        connection = pymongo.Connection()
    except:
        print "connectToDatabase() - Failed to open connect to MongoDB"
        raise

    try:
        db = connection[table_name]
    except:
        print "connectToDatabase() - Failed to connect to %s" % table_name
        raise

    return db


def get_restaurant_entry(result):
    critics_pic = True if result.find(attrs={"class" : "criticsPick"}) else False
    all_links = result.findAll("a")
    link = all_links[0] #result.a
    name = link.string
    url = link['href']
    paragraphs = result.findAll("p")
    desc_short = paragraphs[0].string
    address = paragraphs[1].string
    user_review_url = all_links[1]['href']
    map_url = all_links[2]['href']
    restaurant = {"name":name, "url":url, "address":address, 
                  "desc_short":desc_short, "user_review_url":user_review_url, 
                  "map_url":map_url, "critics_pic":critics_pic}
    return restaurant


def get_restaurant_review(soup):
    
    listing = soup.find(attrs={"class" : "listing item vcard"})

    summary = listing.find(attrs={'class' : 'listing-summary'})
    name = summary.h1.string

    # Get the address info
    address_info = summary.find(attrs={'class' : 'summary-address'})
    street_address = address_info.find(attrs={'class' : 'street-address'}).string
    locality = address_info.find(attrs={'class' : 'locality'}).string
    region = address_info.find(attrs={'class' : 'region'}).string
    postal_code = address_info.find(attrs={'class' : 'postal-code'}).string
    latitude = address_info.find(attrs={'class' : 'latitude'}).string
    longitude = address_info.find(attrs={'class' : 'longitude'}).string

    # Get the summary info
    summary_details = summary.find(attrs={'class' : 'summary-details'})

    score_field = summary_details.find(attrs={'class' : 'average'})
    if score_field != None:
        average_score = summary_details.find(attrs={'class' : 'average'}).string
        best = summary_details.find(attrs={'class' : 'best'}).string
    else:
        average_score = None
        best = None

    category_string = summary_details.find(attrs={'class' : 'category'}).get_text()
    category_string = category_string.replace("Scene: ", "")
    categories = category_string.split(',')

    # Get the review
    review_section = listing.find(attrs={'class' : 'listing-review'}).findAll('p')
    review = ''.join([ item.get_text().strip() for item in review_section])
    review = review.replace('\r', '').replace('\n', '')

    info = {'name' : name, 'street_address' : street_address, 'locality' : locality,
              'region' : region, 'postal_code' : postal_code, 
              'latitude' : latitude, 'longitude' : longitude,
              'average_score' : average_score, 'best' : best, 'categories': categories,
              'review' : review}
    return info


def get_new_restaurants(url, max_pages=50):

    database = connectToDatabase("barkov_chain")
    nymag = database['nymag']

    current_url = url
    current_page = 0

    while current_page < max_pages:

        current_page += 1
        print "Getting url: ", current_url

        # Sleep for 1 sec
        time.sleep(1.0)

        request = urllib2.Request(current_url)
        response = urllib2.urlopen(request)
        soup = BeautifulSoup(response)

        # Get the 'next' url
        current_url = soup.find(attrs={"id" : 'sitewidePrevNext'}).find(attrs={"class" : "nextActive"})['href'] #.string  findAll("a")[1]
        restaurants = soup.find(attrs={ "id" : "resultsFound"}).findAll(attrs={"class" : "result"})

        for result in restaurants:
            restaurant = get_restaurant_entry(result)
            print restaurant['name']
            key = {"name" : restaurant['name'], 
                   "url" : restaurant['url']}
            nymag.update(key, restaurant, upsert=True)
        print '\n'

    return


def get_reviews(num_reviews_to_fetch):

    """
    url = "http://nymag.com/listings/bar/disiac-lounge/"
    request = urllib2.Request(url)
    response = urllib2.urlopen(request)
    soup = BeautifulSoup(response)
    review = get_restaurant_review(soup)
    print review
    return
    """

    database = connectToDatabase("barkov_chain")
    nymag = database['nymag']

    entries = nymag.find({ 'review' : {'$exists':False} },
                         limit = num_reviews_to_fetch)    
    
    for entry in entries:

        url = entry['url']        
        print "Getting review for: ", entry['name'],
        print " from url: ", url
        time.sleep(1.0)

        request = urllib2.Request(url)
        response = urllib2.urlopen(request)
        soup = BeautifulSoup(response)
        if soup==None:
            print "Error: soup is None"
            raise Exception()

        review = get_restaurant_review(soup)
        name = review.pop('name')
        if name != entry['name']:
            print "Error: Entry names don't match: ",
            print repr(name), repr(entry['name'])
            raise Exception()

        entry.update(review)
        key = {"_id": entry['_id']}
        nymag.update(key, entry)
        

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Scrape data from NYMag.')
    parser.add_argument('--scrape_url', '-s', dest='scrape_url', 
                        default=None, help='url to scrape restaurants from')
    parser.add_argument('--fetch_reviews', '-f', dest='fetch_reviews', type=int, 
                        default=None, help='number of reviews to fetch')
    args = parser.parse_args()

    #url = 'http://nymag.com/srch?t=bar&N=259+69&No=0&Ns=nyml_sort_name%7C0'
    url = args.scrape_url
    if url != None:
        get_new_restaurants(url)

    reviews_to_fetch = args.fetch_reviews
    if reviews_to_fetch != None:
        get_reviews(reviews_to_fetch)

