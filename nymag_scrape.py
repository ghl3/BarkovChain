
import time
import urllib2
from bs4 import BeautifulSoup

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


def main():

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

if __name__ == "__main__":
    main()


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
