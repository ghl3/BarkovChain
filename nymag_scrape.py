
import argparse
import sys
import re
import time
import urllib2
import nltk

import pymongo
import bson.objectid
from bs4 import BeautifulSoup

from database import connect_to_database
from database import BadDBField


# def connect_to_database(table_name="barkov_chain"):
#     """ 
#     Get a handle on the db object
#     """

#     try:
#         #connection = pymongo.Connection()
#         connection = pymongo.MongoClient()
#     except ConnectionFailure:
#         message = "connect_to_database() - Failed to open connect to MongoDB \n"
#         message += "Make sure that the MongoDB daemon is running."
#         sys.stderr.write(message)
#         raise

#     try:
#         db = connection[table_name]
#     except InvalidName:
#         message = "connect_to_database() - Failed to connect to %s" % table_name
#         sys.stderr.write(message)
#         raise

#     return db, connection


def get_restaurant_entry(result):
    """
    Return a dict with a the restaurant's listing
    Takes a BeautifulSoup4 object
    """
    critics_pic = True if result.find(attrs={"class" : "criticsPick"}) else False
    all_links = result.findAll("a")
    link = all_links[0]
    name = link.string
    url = link['href']
    paragraphs = result.findAll("p")
    desc_short = paragraphs[0].string
    address = paragraphs[1].string
    user_review_url = all_links[1]['href']
    map_url = all_links[2]['href']
    if map_url == "javascript:void(null)":
        map_url == None
    restaurant = {"name":name, "url":url, "address":address, 
                  "desc_short":desc_short, "user_review_url":user_review_url, 
                  "map_url":map_url, "critics_pic":critics_pic}

    # Do some error checking
    for key, val in restaurant.iteritems():
        if val == '' or val == None:
            if val == None and key == "map_url": continue
            message = "In getting restaurant entry, %s is invalid" % key
            sys.stderr.write(message)
            raise BadDBField(key, val)

    return restaurant


def get_restaurant_review(soup):
    """
    Return the review dict of a restaurant
    Takes a BeautifulSoup4 object
    """
    #listing = soup.find(attrs={"class" : "listing item vcard"})
    #summary = listing.find(attrs={'class' : 'listing-summary'})
    summary = soup.find(attrs={'class' : 'listing-summary'})
    name = summary.h1.string

    # Get the address info
    try:
        address_info = summary.find(attrs={'class' : 'summary-address'})
        street_address = address_info.find(attrs={'class' : 'street-address'}).string
        locality = address_info.find(attrs={'class' : 'locality'}).string
        region = address_info.find(attrs={'class' : 'region'}).string
        latitude = address_info.find(attrs={'class' : 'latitude'}).string
        longitude = address_info.find(attrs={'class' : 'longitude'}).string
    except AttributeError:
        raise BadDBField()

    postal_code_field = address_info.find(attrs={'class' : 'postal-code'})
    if postal_code_field != None:
        postal_code = postal_code_field.string #address_info.find(attrs={'class' : 'postal-code'}).string
    else:
        postal_code = None

    # Get the summary info
    summary_details = summary.find(attrs={'class' : 'summary-details'})
    score_field = summary_details.find(attrs={'class' : 'average'})
    if score_field != None:
        average_score = summary_details.find(attrs={'class' : 'average'}).string
        best = summary_details.find(attrs={'class' : 'best'}).string
    else:
        average_score = None
        best = None
    category_field = summary_details.find(attrs={'class' : 'category'})
    if category_field != None:
        category_string = category_field.get_text()
        category_string = category_string.replace("Scene: ", "")
        categories = category_string.split(',')
        if len(categories) == 0:
            raise RuntimeError()
    else:
        categories = None

    # Get the review
    #review_section = listing.find(attrs={'class' : 'listing-review'}).findAll('p')
    review_section = soup.find(attrs={'class' : 'listing-review'}).findAll('p')
    if len(review_section)==0:
	    review=None
    else:
        review = ''.join([ item.get_text().strip() for item in review_section])
	review = review.replace('\r', '').replace('\n', '')

    info = {'name' : name, 'street_address' : street_address, 'locality' : locality,
              'region' : region, 'postal_code' : postal_code, 
              'latitude' : latitude, 'longitude' : longitude,
              'average_score' : average_score, 'best' : best, 'categories': categories,
              'review' : review}

    # Do some error checking
    for key, val in info.iteritems():
        if val == '' or val == None:
            if val == None and key == 'average_score': continue
            if val == None and key == 'best': continue
            if val == None and key == 'categories': continue
            if val == None and key == 'postal_code': continue
            if val == None and key == 'review': continue
            message = "In getting restaurant review, %s is invalid" % key
            sys.stderr.write(message)
            raise BadDBField(key, val)

    return info


def get_new_restaurants(db, url, max_pages=50):
    """
    Add a number of restaurant entries to the db
    Takes a url for a NYMag restaurant search result page
    and a maximum number of pages to move through
    """
    #nymag = database['bars']
    nymag = db

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
        if soup == None:
            sys.stderr.write("Invalid URL supplied: " + current_url)
            raise RuntimeError()

        # Get the 'next' url
        current_url = soup.find(attrs={"id" : 'sitewidePrevNext'}) \
            .find(attrs={"class" : "nextActive"})['href'] 
        restaurants = soup.find(attrs={ "id" : "resultsFound"}) \
            .findAll(attrs={"class" : "result"})

        for result in restaurants:
            restaurant = get_restaurant_entry(result)
            print restaurant['name']
            entry = {'nymag' : restaurant}
            key = {"nymag.name" : restaurant['name'], 
                   "nymag.url" : restaurant['url']}
            print "Adding: ", key, entry
            #nymag.update(key, entry, upsert=True)
            print "NOT UPDATING"
        print '\n'

    return


def get_reviews(db, num_reviews_to_fetch):
    """
    Loop through the database, 
    find a number of restaurants that don't have reviews,
    download their reviews, and append them to the db
    """

    """
    url = "http://nymag.com/listings/bar/disiac-lounge/"
    request = urllib2.Request(url)
    response = urllib2.urlopen(request)
    soup = BeautifulSoup(response)
    review = get_restaurant_review(soup)
    print review
    return
    """

    #database = connect_to_database("barkov_chain")
    #nymag = database['bars']
    nymag = db['bars']

    entries = nymag.find({ 'nymag.review' : {'$exists':False} },
                         limit = num_reviews_to_fetch)    

    failures = []
    
    for entry in entries:

        name = entry['nymag']['name']
        url = entry['nymag']['url']        
        print "Getting review for: ", name,
        print "from url: ", url
        time.sleep(1.0)

        request = urllib2.Request(url)
        response = urllib2.urlopen(request)
        soup = BeautifulSoup(response)
        if soup==None:
            sys.stderr.write("Error: soup is None")
            raise RuntimeError()

        try:
            review = get_restaurant_review(soup)
        except BadDBField:
            print "Skipping url: ", url
            failures.append(entry)
            continue

        review_name = review.pop('name')
        if review_name != name:
            message = "Error: Entry names don't match: "
            message += repr(name) + ' ' + repr(entry['name'])
            sys.stderr.write(message)
            raise RuntimeError()

        entry['nymag'].update(review)
        key = {"_id": entry['_id']}
        print "Updating:", key, entry
        print "NOT UPDATING"
        #nymag.update(key, entry)

    if len(failures) > 0:
        print "Failed to get reviews for the following:"
        for failure in failures:
            print failure

    return

    
    

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Scrape data from NYMag.')
    parser.add_argument('--scrape_url', '-s', dest='scrape_url', 
                        default=None, help='url to scrape restaurants from')
    parser.add_argument('--fetch_reviews', '-f', dest='fetch_reviews', type=int, 
                        default=None, help='number of reviews to fetch')
    parser.add_argument('--clear', '-c', dest='clean', type=int, 
                        default=None, help='clean up the database')
    args = parser.parse_args()

    db, connection = connect_to_database()

    try:
        url = args.scrape_url
        if url != None:
            get_new_restaurants(db, url)

        reviews_to_fetch = args.fetch_reviews
        if reviews_to_fetch != None:
            get_reviews(db, reviews_to_fetch)

        num_to_clean = args.clean
        if num_to_clean != None:
            clean(db, num_to_clean)

    except (pymongo.errors.ConnectionFailure, pymongo.errors.InvalidName) as err:
        print err
        connection.disconnect()
        sys.exit(1)

    except Exception as err:
        print err
        connection.disconnect()
        raise

    connection.disconnect()
    sys.exit(0)
