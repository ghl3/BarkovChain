
import re
import time
import urllib2
from bs4 import BeautifulSoup
import nltk

import pymongo
import bson.objectid


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
                  "desc_short":desc_short,"user_review_url":user_review_url, 
                  "map_url":map_url, "critics_pic":critics_pic}
    return restaurant


def get_new_restaurants():

    database = connectToDatabase("barkov_chain")
    nymag = database['nymag']

    current_url = 'http://nymag.com/srch?t=bar&N=259+69&No=0&Ns=nyml_sort_name%7C0'
    current_page=0

    while current_page < 50:

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


def get_reviews():
    #database = connectToDatabase("barkov_chain")
    #nymag = database['nymag']

    url = "http://nymag.com/listings/bar/disiac-lounge/"

    request = urllib2.Request(url)
    response = urllib2.urlopen(request)
    soup = BeautifulSoup(response)
    
    listing = soup.find(attrs={"class" : "listing item vcard"})
    #print listing    

    summary = listing.find(attrs={'class' : 'listing-summary'})
    name = summary.h1.string

    address_info = summary.find(attrs={'class' : 'summary-address'})
    street_address = address_info.find(attrs={'class' : 'street-address'}).string
    locality = address_info.find(attrs={'class' : 'locality'}).string
    region = address_info.find(attrs={'class' : 'region'}).string
    postal_code = address_info.find(attrs={'class' : 'postal-code'}).string
    latitude = address_info.find(attrs={'class' : 'latitude'}).string
    longitude = address_info.find(attrs={'class' : 'longitude'}).string

    print name, street_address, locality, region, postal_code, latitude, longitude

    summary_details = summary.find(attrs={'class' : 'summary-details'})
    
    review = summary_details.find(attrs={'class' : 'average'}).string
    best = summary_details.find(attrs={'class' : 'best'}).string
    category_string = summary_details.find(attrs={'class' : 'category'}).get_text()
    category_string = category_string.replace("Scene: ", "")
    categories = category_string.split(',')
    print review, best, categories

    #result = re.match("Scene: (?.+[,])*.*", category_string)
    #print result.groups()

    #for match in result.group():
    #    print match

    review_section = listing.find(attrs={'class' : 'listing-review'}).findAll('p')
    review = ''.join([ item.get_text().strip() for item in review_section])
    review = review.replace('\r', '').replace('\n', '')
    print repr(review)
    #for item in review_section:
    #    print item.get_text()
    #review_section = listing.find(attrs={'class' : 'listing-review'}).get_text()

    #print review_section
    #review = review_section.get_text()
    #review = nltk.clean_html(review)
    #print review


if __name__ == "__main__":
    #get_new_restaurants()
    get_reviews()


"""
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
restaurant = {"name":name, "url":url, "address":address, "desc_short":desc_short,
"user_review_url":user_review_url, "map_url":map_url, 
"critics_pic":critics_pic}
# Search by name and url
"""
