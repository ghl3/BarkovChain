
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

    url = 'http://nymag.com/srch?t=bar&N=259+69&No=0&Ns=nyml_sort_name%7C0'
    request = urllib2.Request(url)
    response = urllib2.urlopen(request)
    soup = BeautifulSoup(response)

    restaurants = soup.find(attrs={ "id" : "resultsFound"}).findAll(attrs={"class" : "result"})

    for result in restaurants:
        restaurant = get_restaurant_entry(result)
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
        key = {"name" : restaurant['name'], 
               "url" : restaurant['url']}
        #nymag.update(key, restaurant, upsert=True)
        #restaurant_id = nymag.save( restaurant )
        print restaurant

    return

    for user in page_users:
        name = user['href'].strip('/user/') 
        if name not in excluded_users:
            all_users.append(name)
            pass

    return all_users, checked_pages


if __name__ == "__main__":
    main()
