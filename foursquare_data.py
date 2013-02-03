
import argparse
import time
import json
import os
import foursquare
import nltk
import unicodedata

from database import connect_to_database
from database import BadDBField, APIError

'''
To Do:
import foursquare tips

To the mapping using 'suggest location':
https://developer.foursquare.com/docs/explore#req=venues/suggestCompletion%3Fll%3D40.7,-74%26query%3Dfoursqu

Add the foursquare id to the database

Then, loop over events with a foursquare id and
download the tips (and ratings)
'''

#def suggest_completion(api, **kwargs):
#    """https://developer.foursquare.com/docs/venues/explore"""
#    return api.GET('suggest_completion', **kwargs)


def get_credentials():
    """ 
    Query the environment to get
    the FOURSQUARE Client ID and SECRET
    """

    CLIENT_ID = os.environ["FOURSQUARE_CLIENT_ID"]
    CLIENT_SECRET = os.environ["FOURSQUARE_CLIENT_SECRET"]
    return (CLIENT_ID, CLIENT_SECRET)


def get_api():
    """
    Create and return an instance of
    the Foursquare api
    """
    client_id, client_secret = get_credentials()
    #api = foursquare.Foursquare(client_id=client_id,
    #                               client_secret=client_secret,
    #                               redirect_uri='http://fondu.com/oauth/authorize')
    api = foursquare.Foursquare(client_id=client_id,
                     client_secret=client_secret,
                     redirect_uri='http://fondu.com/oauth/authorize')
    return api


def get_foursquare_id(api, name, longitude, latitude, radius=100):
    """
    Based on the name and location,
    get a guess for the foursquare
    version and return the id
    """
    ll = "{lat},{lon}".format(lat=latitude, lon=longitude)
    #response = suggest_completion(api.venues, query=name, ll=ll)
    params = {'query': name, 'll':ll, 'radius':radius}
    response = api.venues.suggestcompletion(params=params)

    matches = []

    if u'minivenues' not in response:
        raise APIError()
    venues = response[u'minivenues']
    if len(venues)==0:
        return None, None

    for venue in venues:
        venue_name = venue[u'name']
        distance = nltk.metrics.edit_distance(name, venue_name)
        matches.append((venue, distance))
        
    matches.sort(key=lambda x: x[1])

    return matches[0]


def match_foursquare_id(db, api, num_to_match=10):
    """
    Get the corresponding foursquare id to the
    given location.
    """
    bars = db['bars']
    
    # Find bars without a foursquare entry
    entries = bars.find({ 'foursquare' : {'$exists':False}},
                        limit = num_to_match)

    failures = []

    for entry in entries:

        time.sleep(1.0)

        print "Trying Entry:"
        print entry

        try:
            nymag = entry['nymag']
            name = nymag['name']
            lon = nymag['longitude']
            lat = nymag['latitude']
        except (AttributeError, KeyError):
            print "Failed to match id for entry:"
            print entry
            failures.append(entry)
            continue

        ascii_name = unicodedata.normalize('NFKD', name).encode('ascii','ignore')

        if len(ascii_name) < 3: 
            print "Can't get match for foursquare, name is too short: ", name
            fsq_match = None
        else:
            fsq_match, distance = get_foursquare_id(api, ascii_name, lon, lat)

        if fsq_match==None: 
            print "Failed to find match for: ", name
            distance = None
        else:
            fsq_match['distance_to_nymag'] = distance
            print fsq_match['name'], nymag['name'],

        #print fsq_match
        #(fsq_name, fsq_id) = (fsq_match[u'name'], fsq_match[u'id'])
        #print "Adding foursquare id for nymag name: %s " % name,
        #print "fsq name: %s distance: %s" % (fsq_name, distance)
        #foursquare_info = {'foursquare_name' : fsq_name,
        #                   'foursquare_id' : fsq_id,
        #                   'foursquare_nymag_overlap' : distance}
        #entry['foursquare']['distance_to_nymag'] = distance

        entry['foursquare'] = fsq_match
        db_key = {"_id": entry['_id']}
        print db_key, entry
        bars.update(db_key, entry)

    if len(failures) > 0:
        print "Failed to get reviews for the following:"
        for failure in failures:
            print failure

    return


def get_tip_list(api, foursquare_id):
    """
    Get a set of tips for the given venue with foursquare_id
    """

    keys_to_keep = ['text', 'id']

    params = {"limit" : 500, 'sort' : 'popular'}
    response = api.venues.tips(foursquare_id, params=params)
    tips = response['tips']['items']

    info_list = []

    for tip in tips:
        info = {}
        for key in keys_to_keep:
            info[key] = tip[key]
        info_list.append(info)

    return info_list


def add_tips_to_db(db, api, num_to_match=10):
    """
    Find db entries without foursquare tips
    and add the tip to those entries
    """

    bars = db['bars']
    
    # Find bars with a foursquare entry
    # but without foursquare tips
    entries = bars.find({ 'foursquare' : {'$exists':True},
                          'foursquare' : {'$ne':None},
                          'foursquare.tips' : {'$exists':False}},
                        limit = num_to_match)

    failures = []

    for entry in entries:
        
        time.sleep(1.0)

        print "Trying Entry:"
        print entry

        try:
            foursquare_id = entry['foursquare']['id']
        except (AttributeError, KeyError):
            print "Failed to get tip for entry:"
            print entry
            failures.append(entry)
            continue

        tip_list = get_tip_list(api, foursquare_id)
        entry['foursquare']['tips'] = tip_list

        db_key = {"_id": entry['_id']}
        print db_key, entry
        bars.update(db_key, entry)

        print '\n'

    if len(failures) > 0:
        print "Failed to get reviews for the following:"
        for failure in failures:
            print failure


def get_nearby_venues(api, latitude, longitude, radius=800):
    """
    Return a list of venues
    Based on api:
    https://developer.foursquare.com/docs/venues/search

    Each venue is defined by:
    https://developer.foursquare.com/docs/responses/venue

    Radius in meters
    """

    params = {}
    params['query'] = 'coffee'
    params['radius'] = radius
    params['ll'] = '%.4s,%.4s' % (latitude, longitude)
    params['intent'] = 'browse'
    params['limit'] = 50
    response = api.venues.search(params=params)
    venues = response[u'venues']

    return venues


def main():

    parser = argparse.ArgumentParser(description='Scrape data from NYMag.')
    parser.add_argument('--match', '-m', dest='match', type=int, default=None, 
                        help='Find the closest matching foursquare location to a nymag location')
    parser.add_argument('--tips', '-t', dest='tips', type=int, default=None, 
                        help='Add foursquare tips to the database')
    args = parser.parse_args()

    # Get the mongo database
    db, connection = connect_to_database()

    # Get the foursquare api
    try:
        api = get_api()
    except KeyError:
        print "Cannot get foursquare info from environment"
        print "Ensure that your environment is properly setup by sourcing 'setup.sh'"
        return 255
    auth_uri = api.oauth.auth_url()

    num_to_match = args.match
    if num_to_match != None:
        match_foursquare_id(db, api, num_to_match)

    tips_to_get = args.tips
    if tips_to_get != None:
        add_tips_to_db(db, api, tips_to_get)

    return

##############

    matches = get_foursquare_id(api, "art bar", longitude=-74.00355,
                                 latitude=40.738491)
    for match in matches:
        print match
    return

    #venues = get_nearby_venues(api,"40.728625","73.997684")
    #venues = get_nearby_venues(api,"44.3","37.2")
    venues = get_nearby_venues(api, 40.7, -74)

    print venues
    return

    for venue in venues:
        print venue
    return

    params = {}
    params['query'] = 'coffee'
    params['near'] = 'New York'
    params['intent'] = 'browse'
    params['limit'] = 15
    response = client.venues.search(params=params)

    geocode = response[u'geocode']
    venues = response[u'venues']

    for key, val in geocode['feature'].iteritems():
        print key, val
    return

    for venue in venues:
        print venue
        for key, val in venue.iteritems():
            print key, val

if __name__ == "__main__":
    main()
