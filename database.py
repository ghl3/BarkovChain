
import sys
import argparse

import pymongo
import bson.objectid

import os
from urlparse import urlparse

from pymongo.errors import ConnectionFailure
from pymongo.errors import InvalidName


class BadDBField(Exception):
    pass	

class APIError(Exception):
    pass


def connect_to_database(table_name="barkov_chain"):
    """ 
    Get a handle on the db object
    """

    """
    MONGO_URL = os.environ.get('MONGOHQ_URL')

    if MONGO_URL:
        # Get a connection
        connection = Connection(MONGO_URL)
        # Get the database
        db = connection[urlparse(MONGO_URL).path[1:]]
    else:
        # Not on an app with the MongoHQ add-on, do some localhost action
        connection = Connection('localhost', 27017)
        db = connection['MyDB']
    """

    print "Connecting to database"

    MONGO_URL = os.environ.get('MONGOHQ_URL')

    if MONGO_URL:

        print "Using REMOTE MongoDB Server"

        # Get a connection
        try:
            connection = pymongo.Connection(MONGO_URL)
        except ConnectionFailure:
            message = "connect_to_database() - Failed to open connect to REMOTE MongoHQ \n"
            sys.stderr.write(message)
            raise
        
        # Get the database
        try:
            db_name = urlparse(MONGO_URL).path[1:]
            db = connection[db_name]
        except InvalidName:
            message = "connect_to_database() - Failed to connect to %s" % table_name
            raise

    else: 

        print "Using LOCAL MongoDB Server"

        try:
            connection = pymongo.MongoClient()
        except ConnectionFailure:
            message = "connect_to_database() - Failed to open connect to MongoDB \n"
            message += "Make sure that the MongoDB daemon is running."
            sys.stderr.write(message)
            raise

        try:
            db = connection[table_name]
        except InvalidName:
            message = "connect_to_database() - Failed to connect to %s" % table_name
            sys.stderr.write(message)
            raise
    
    print "Successfully connected to database"
        
    return db, connection


def valid_entry_dict():
    """
    A query string defining a valid
    entry in the Mongo DB
    """
    
    criteria = { 
        'nymag' : {'$exists':True}, 
        'foursquare' : {'$exists':True}, 
        'nymag.review' : {'$exists':True, '$ne':None }, 
        'nymag.categories' : {'$exists':True, '$ne':None }, 
#        'nymag.review' : {}, 
        'foursquare.tips' : {'$exists':True, '$ne':None}, 
#        'foursquare.tips' : {}, 
        'foursquare.distance_to_nymag' : {'$exists':True, '$lte':6} 
        }

    return criteria


def reformat_database(db, num_to_reformat):
    """
    Take all entries and collect them
    into 'nymag' and 'foursquare'

    """
    bars = db['bars']    

    entries = bars.find({ 'foursquare' : {'$exists':False},
                          'nymag' : {'$exists':False}
                          },
                        limit = num_to_reformat)    
    
    total = 0
    # Get everything in the entry.  We assume that it is
    # all from nymag for now
    for entry in entries:

        nymag = {}
        for key in entry.keys():
            if key == '_id':
                continue
            nymag[key] = entry[key]
            del entry[key]

        entry['nymag'] = nymag
        db_key = {u"_id": entry['_id']}
        print "Updating: ", db_key, entry, '\n'
        #print entry, nymag
        bars.update(db_key, entry)
        total += 1
    
    print "Updated %s entries" % total


def acceptable_location(location):
    for category in location['nymag']['categories']:
        if "Gay" in category: return False
    return True

def clean_lon_lat(db, num_to_clean):
    """
    Convert any lon, lat unicode
    strings into floats
    """
    
    nymag = db['bars']

    entries = nymag.find({ 'longitude' : {'$type' : 2} },
                         limit = num_to_clean)    

    for entry in entries:

        longitude = float(entry['longitude'])
        latitude = float(entry['latitude'])
        entry['longitude'] = longitude
        entry['latitude'] = latitude
        if longitude == None or latitude == None:
            print "Failed to update: %s" % entry['name']
            continue
        print "Updating: %s with (%s, %s)" % (entry['name'], longitude, latitude)
        key = {"_id": entry['_id']}
        nymag.update(key, entry)

    return


def main():

    parser = argparse.ArgumentParser(description='Database utilities.')
    parser.add_argument('--reformat', '-r', dest='reformat', type=int, 
                        default=None, help='Reformat database')
    parser.add_argument('--clean', '-c', dest='clean', type=int, 
                        default=None, help='Clean: Number of databse entries to clean')
    args = parser.parse_args()

    db, connection = connect_to_database()

    num_to_clean = args.clean
    if num_to_clean != None:
        clean_lon_lat(db, num_to_clean)

    num_to_reformat = args.reformat
    if num_to_reformat != None:
        reformat_database(db, num_to_reformat)


if __name__ == "__main__":
    main()

