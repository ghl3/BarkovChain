#!/usr/bin/env python

from __future__ import division

import os
import random
import math
import json
import random
import itertools

from flask import Flask
from flask import render_template
from flask import request
from flask import jsonify
from flask import Response
from bson import json_util
from bson import ObjectId

from database import connect_to_database
from database import valid_entry_dict

import geopy
import geopy.distance

import scipy.stats

from lsa import LSA


# Create the lsa object and load
# its parameters from disk
lsa = LSA()
lsa.load()

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/initial_location', methods=['POST'] )
def api_initial_location():
    """
    Take lat/lon coordinates and return
    the initial location, as well as the
    initial user vector.

    Input - Takes a dictionary with a 'location' key
    consisting of 'latitude' and 'longitude':

    {'latitude' : lat, 'longitude' : lon}

    Output - Return a dictionary consisting of the 
    location dict, the id in the database, and the
    updated user preference vector:

    { 'location' : {'_id' : id, ...}, 'user_vector' : [...]}
    """

    if 'json' not in request.headers['Content-Type']:
        print "Bad Content-Type : Expected JSON"
        return not_found()

    # Get the next location
    marker_location = request.json['location']
    marker_location['initial'] = True
    current_chain = [marker_location]
    next_location = get_next_location(current_chain, rejected_locations=[])

    # Update the user vector
    user_vector = lsa.get_svd_document_vector(next_location['nymag']['name'])
    user_vector = [val for val in user_vector]
    
    # Return the data
    data_for_app = {}
    data_for_app['location'] = next_location['nymag']
    data_for_app['location']['_id'] = str(next_location['_id'])
    data_for_app['user_vector'] = user_vector

    js = json.dumps(data_for_app, default=json_util.default)
    resp = Response(js, status=200, mimetype='application/json')

    return resp


@app.route('/api/next_location', methods=['POST'] )
def api_next_location():
    """
    Return the next location in the chain

    Input - A 'chain' list of previously visited
    location, a list of "rejected_locations' to not
    consider, whether or not the user accepted or 
    rejected the last point, and the user's 
    preference vector:
    { 'chain' : [{...}, {...}, ...],
      'rejected_locations' : [...],
      'accepted' : True (False),
      'user_vector' : [...] }

    Output - Return a dictionary consisting of the 
    location dict, the id in the database, and the
    updated user preference vector:

    { 'location' : {'_id' : id, ...}, 'user_vector' : [...]}
    """

    # Check content type (only json for now)
    # Be tolerent when recieving, 
    # be string when sending
    if 'json' not in request.headers['Content-Type']:
        print "Bad Content-Type : Expected JSON"
        return not_found()

    current_chain = request.json['chain']
    rejected_locations = request.json['rejected_locations']
    accepted = request.json['accepted']
    user_vector = request.json['user_vector']

    # Update the user's semantic vector based on
    # whether he accepted or rejected the last location
    user_vector = update_user_vector(user_vector, current_chain[-1], 
                                     accepted, len(current_chain))

    # Get the next location, package it up
    # and send it to the client
    next_location = get_next_location(current_chain, rejected_locations)

    data_for_app = {}
    data_for_app['location'] = next_location['nymag']
    data_for_app['location']['_id'] = str(next_location['_id'])
    data_for_app['user_vector'] = user_vector

    js = json.dumps(data_for_app, default=json_util.default)
    resp = Response(js, status=200, mimetype='application/json')
    #resp.headers['Link'] = 'http://luisrei.com'
    return resp


@app.errorhandler(400)
def invalid_content(error=None):
    message = {
        'status': 400,
        'message': 'invalid body content'
        }
    resp = jsonify(message)
    resp.status_code = 400
    return resp

@app.errorhandler(403)
def not_found(error=None):
    message = {
        'status': 403,
        'message': 'Forbidden'
        }
    resp = jsonify(message)
    resp.status_code = 403
    return resp

@app.errorhandler(404)
def not_found(error=None):
    message = {
        'status': 404,
        'message': 'Not Found: ' + request.url,
        }
    resp = jsonify(message)
    resp.status_code = 404
    return resp


def get_lat_lon_square_query(current_location, blocks):
    """
    Return the min/max of lat and lon
    to be used in the query's bounding box.
    """

    lat, lon = current_location['latitude'], current_location['longitude']
    
    # New York Block dimensions
    block_lat = 0.0003
    block_lon = 0.001

    lat_min = lat - blocks*block_lat
    lat_max = lat + blocks*block_lat
    lon_min = lon - blocks*block_lon
    lon_max = lon + blocks*block_lon

    query = {
        "nymag.latitude": {"$gt": lat_min, "$lt": lat_max},
        "nymag.longitude": {"$gt": lon_min, "$lt": lon_max}
        }

    #return (lat_min, lat_max), (lon_min, lon_max)
    return query


def get_next_location(current_chain, rejected_locations, user_vector=None):
    """
    Return the next location based on the user's current
    preference vector, his current location, and the list
    of rejected (blacklisted) locations.

    Return the next location based on the current markov chain.

    'current_chain' is a list of location dictionaries that
    was sent from the javascript GET request

    We return a single dictionary containing the information
    about the next location.

    The 'initial' boolean determines if this will be the first
    entry or not.  This is passed to the 'monte carlo' function

    Return a list
    """

    current_location = current_chain[-1]

    # Ensure no reject or current ids are selected
    used_ids = [ObjectId(location['_id']) 
                for location in itertools.chain(current_chain, rejected_locations) 
                if '_id' in location]

    # Build the db query
    blocks=10
    db_query = {}
    db_query.update(get_lat_lon_square_query(current_location, blocks=blocks))
    db_query.update(valid_entry_dict())
    db_query.update( {'_id' : {'$nin' : used_ids}})

    # Get the nearby locations
    db, connection = connect_to_database(table_name="barkov_chain")
    bars = db['bars']
    proposed_locations = list(bars.find(db_query))

    # If we didn't grab enough locations,
    # try a larger search block
    while len(proposed_locations) < 5:
        print "Too few nearby locations found within %s blocks (%s).",
        print "Extending query: %s %s" % (blocks, len(proposed_locations))
        blocks += 10
        updated_distance = get_lat_lon_square_query(current_location, blocks=blocks)
        db_query.update(updated_distance)
        proposed_locations = list(bars.find(db_query))

    # Select the next location in the chain
    next_location = next_location_from_mc(proposed_locations, current_location, user_vector)

    return next_location


def get_initial_location(locations):
    """
    Get the initial starting point.
    The algorithm for this is differnet since we
    don't yet have a chain of location or a
    user vector defined.
    It is therefore based only on long/lat
    """
    pass
    

def next_location_from_mc(proposed_locations, current_location, user_vector):
    """
    Here, we implement the markov chain and pick the next location.

    We simply get the probability of transition and throw
    a random number betwen 0 and 1 to determine if we
    accept it or not.
    """

    # Calculate the total probability for normalization
    total_probability = 0
    for location in proposed_locations:
        total_probability += mc_weight(location, current_location, user_vector)

    # Calculate the weight function
    while True:
        proposed = random.choice(proposed_locations)
        probability = mc_weight(proposed, current_location, user_vector) / total_probability
        mc_throw = random.uniform(0.0, 1.0)
        if probability > mc_throw:
            print "Monte Carlo: probability %s, throw %s" % (probability, mc_throw)
            return proposed
    return


def distance_dr(loc0, loc1):
    """
    Find the distance between two locations
    Inputs are two dictionaries with
    'longitude' and 'latitude'
    Returns result in meters
    """

    lat0, lon0 = loc0['latitude'], loc0['longitude']
    lat1, lon1 = loc1['latitude'], loc1['longitude']

    pt1 = geopy.Point(lat0, lon0)
    pt2 = geopy.Point(lat1, lon1)
    
    dist = geopy.distance.distance(pt1, pt2).km*1000
    return dist


def mc_weight(proposed, current, user_vector):
    """ 
    Calculate the probability of jumping from current to proposed
    """

    probability = 1.0

    name = proposed['nymag']['name']
    initial = current.get('initial', False)

    distance = distance_dr(proposed['nymag'], current)
    distance_pdf = scipy.stats.expon.pdf(distance, scale=200) # size is 100 meters
    probability *= distance_pdf

    # Disfavor non critics-picks
    if proposed['nymag'].get(u'critics_pic', False) != True:
        probability *= .1
        
    # Get the lsa cosine, but only if this isn't
    # the initial marker
    cosine = 1.0
    similarity_pdf = 1.0
    if not initial:
        last_venue_name = current['name']
        try:
            # For now, the 'user_vec' is the vector
            # from the last restaurant
            user_vec = lsa.get_svd_document_vector(last_venue_name)
            cosine = lsa.user_cosine(user_vec, name)
        except KeyError:
            print "Error: Couldn't find venue %s in corpus" % name
            raise
        # Cosine goes from -1 to 1, we add 1 to make it positive definite
        # similarity_pdf = scipy.stats.expon.pdf(cosine+1.0, scale=0.001)
        if cosine > 0:
            similarity_pdf = cosine                
        else:
            similarity_pdf = 0.0000001
        probability *= similarity_pdf
    
    print "Weight Function:", 
    print "Distance(%s m) = %s" % (distance, distance_pdf),
    print "Similarity(%s) = %s" % (cosine, similarity_pdf)

    return probability

"""
{'foursquare': {'distance_to_nymag': 0, u'location': {u'city': u'', u'distance': 44, u'country': u'United States', u'lat': 40.748041, u'state': u'NY', u'crossStreet': u'', u'address': u'', u'postalCode': u'', u'lng': -73.987197}, u'id': u'4e7d3b8bb8f724f0c24f3f7d', u'categories': [{u'shortName': u'Karaoke', u'pluralName': u'Karaoke Bars', u'id': u'4bf58dd8d48988d120941735', u'icon': {u'prefix': u'https://foursquare.com/img/categories/nightlife/karaoke_', u'name': u'.png', u'sizes': [32, 44, 64, 88, 256]}, u'name': u'Karaoke Bar'}], u'name': u'32 Karaoke'}, u'_id': ObjectId('51043ce2d08ce64b3c2f64a6'), u'nymag': {u'average_score': None, u'user_review_url': u'?map_view=1&N=0&No=1&listing_id=75735', u'locality': u'New York', u'url': u'http://nymag.com/listings/bar/32-karaoke/index.html', u'region': u'NY', u'categories': [u'After Hours', u' Karaoke Nights'], u'longitude': -73.987249, u'map_url': u'javascript:void(null)', u'postal_code': u'10001', u'best': None, u'address': u'2 W. 32nd St.', u'latitude': 40.747639, u'critics_pic': False, u'desc_short': u'See the profile of this NYC bar at 2 W. 32nd St. in Manhattan.', u'review': u'Have a BYOB sing-along (till 5 a.m.) without the weekend throngs of students.', u'street_address': u'2 W. 32nd St.', u'name': u'32 Karaoke'}}
"""

def update_user_vector(user_vector, last_location, 
                       accepted, chain_length):
    """
    Update the user's vector 
    based on whether he accepted the last location
    The size of the update is based on how many 
    entries in the chain that we've had so far
    """

    # Get the vector of the last location
    last_loc_name = last_location['name']
    last_loc_vec = lsa.get_svd_document_vector(last_loc_name)
    last_loc_vec = [val for val in last_loc_vec]

    return last_loc_vec


def get_random_locations(number_of_locations=3):
    """
    Return 3 random locations from the database
    """
    
    db, connection = connect_to_database(table_name="barkov_chain")
    nymag = db['bars']
    locations = nymag.find({ 'review' : {'$exists':True} },
                         limit = 100)
    locations = [locations[random.randint(0, 100)] for i in range(number_of_locations)]
    return locations

 
if __name__ == '__main__':
    # Bind to PORT if defined, otherwise default to 5000.
    port = int(os.environ.get('PORT', 5000))
    app.debug = True
    #app.run(host='192.168.1.5', port=8001)
    app.run(host='0.0.0.0', port=port)
