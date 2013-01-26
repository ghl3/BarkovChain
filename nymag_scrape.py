
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


def main():

    database = connectToDatabase("barkov_chain")
    nymag = database['nymag']

    url = 'http://nymag.com/srch?t=bar&N=259+69&No=0&Ns=nyml_sort_name%7C0'
    request = urllib2.Request(url)
    response = urllib2.urlopen(request)
    soup = BeautifulSoup(response)

    restaurants = soup.find(attrs={ "id" : "resultsFound"}).findAll(attrs={"class" : "result"})


    for result in restaurants:
        link = result.a
        name = link.contents
        url = link['href']
        paragraphs = result.findAll("p")
        desc_short = paragraphs[0]
        address = paragraphs[1]
        #desc_short = result.p[0].contents
        #address = result.p[1].contents
        print name, url, address, desc_short
        #raw = result
        #restaurant = {'name' : 
        #print result
        #print restaurant_url.contents, restaurant_url, restaurant_url['href']


    return

    for user in page_users:
        name = user['href'].strip('/user/') 
        if name not in excluded_users:
            all_users.append(name)
            pass

    return all_users, checked_pages


if __name__ == "__main__":
    main()
