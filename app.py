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

import numpy
import scipy.stats

from math import pi
from math import tan                

from lsi import load_lsi

# Create a corpus from this
dictionary, lsi, tfidf, corpus, corpus_lsi_tfidf, \
    lsi_index, bar_idx_map, idx_bar_map = load_lsi()

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
    #user_vector = lsa.get_svd_document_vector(next_location['nymag']['name'])
    bar_index = bar_idx_map[next_location['nymag']['name']]
    initial_user_vector = [var for idx, var in corpus_lsi_tfidf[bar_index]]
    print "Created Initial User Vector: ", 
    print initial_user_vector

    # Return the data
    data_for_app = {}
    data_for_app['location'] = next_location['nymag']
    data_for_app['location']['_id'] = str(next_location['_id'])
    data_for_app['user_vector'] = initial_user_vector

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
      'last
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
    user_vector = request.json['user_vector']
    last_venue = request.json['last_venue']
    accepted = request.json['accepted']

    # Update the user's semantic vector based on
    # whether he accepted or rejected the last location
    user_vector = update_user_vector(user_vector, last_venue, 
                                     accepted, len(current_chain))
    
    # Get the next location, package it up
    # and send it to the client
    next_location = get_next_location(current_chain, rejected_locations, user_vector)

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


class weight(object):
    
    def __init__(self):
        self.probability = None
        self.distance = None
        self.critics_pic = None
        self.cosine = None
        self.words = None

    def __repr__(self):
        repr_str = ''
        repr_str += "Probability = %.5s " % self.probability
        repr_str += "("
        repr_str += "Distance = %.5s, " % self.distance
        repr_str += "Critics Pic = %s, " % self.critics_pic
        repr_str += "Cosine = %.7s" % self.cosine
        repr_str += ")"
        return repr_str


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
    total_probability = 0.0
    while len(proposed_locations) < 5 and total_probability <= 0:
        print "Too few nearby locations found within %s blocks (%s).",
        print "Extending query: %s %s" % (blocks, len(proposed_locations))
        blocks += 10
        updated_distance = get_lat_lon_square_query(current_location, blocks=blocks)
        db_query.update(updated_distance)
        proposed_locations = list(bars.find(db_query))

        for location in proposed_locations:
            weight_result = mc_weight(location, current_location, user_vector)
            total_probability += weight_result.probability

    # Calculate the weight function
    mc_steps = 0
    while True:
        mc_steps += 1
        proposed = random.choice(proposed_locations)
        weight_result = mc_weight(proposed, current_location, user_vector)
        weight_result.probability /= total_probability
        mc_throw = random.uniform(0.0, 1.0)
        if weight_result.probability > mc_throw:
            print "Monte Carlo Converged after %s throws: " % mc_steps,
            print weight_result
            print "Words in Selected: ", weight_result.words
            if user_vector:
                print "User Vector: ", ["%.5f" % val for val in user_vector]
            return proposed

    return None



#     # Select the next location in the chain
#     next_location = next_location_from_mc(proposed_locations, total_probability,
#                                           current_location, user_vector)

#     return next_location


# def next_location_from_mc(proposed_locations, total_probability,
#                           current_location, user_vector):
#     """
#     Here, we implement the markov chain and pick the next location.

#     We simply get the probability of transition and throw
#     a random number betwen 0 and 1 to determine if we
#     accept it or not.
#     """

#     # Calculate the total probability for normalization
#     total_probability = 0
#     for location in proposed_locations:
#         weight_result = mc_weight(location, current_location, user_vector)
#         total_probability += weight_result.probability

#     # Calculate the weight function
#     mc_steps = 0
#     while True:
#         mc_steps += 1
#         proposed = random.choice(proposed_locations)
#         weight_result = mc_weight(proposed, current_location, user_vector)
#         weight_result.probability /= total_probability
#         mc_throw = random.uniform(0.0, 1.0)
#         if weight_result.probability > mc_throw:
#             print "Monte Carlo Converged after %s throws: " % mc_steps,
#             print weight_result
#             print "Words in Selected: ", weight_result.words
#             if user_vector:
#                 print "User Vector: ", ["%.5f" % val for val in user_vector]
#             return proposed
#     return


def mc_weight(proposed, current, user_vector):
    """ 
    Calculate the probability of jumping from current to proposed
    """

    result = weight()
    probability = 1.0

    name = proposed['nymag']['name']
    initial = current.get('initial', False)

    distance = distance_dr(proposed['nymag'], current)
    distance_pdf = scipy.stats.expon.pdf(distance, scale=300) # size is 100 meters
    probability *= distance_pdf

    # Disfavor non critics-picks
    critics_pic = False
    if proposed['nymag'].get(u'critics_pic', False):
        critics_pic = True
    else:
        probability *= .5
        
    # Get the lsa cosine, but only if this isn't
    # the initial marker
    cosine = None
    #similarity_pdf = 1.0
    if not initial:
        try:
            # User vector lives in the lsa[tfidf] space
            user_array = numpy.array(user_vector)
            sims = lsi_index[user_array]
            proposed_bar_idx = bar_idx_map[name]
            cosine = sims[proposed_bar_idx]
            result.words = [dictionary[pair[0]] for pair in corpus[proposed_bar_idx]]
        except:
            print "Cosine Error"
            raise

        # We here directly use the cosine as the pdf, but one
        # could be smarter about this
        # similarity_pdf = scipy.stats.expon.pdf(cosine+1.0, scale=0.001)
        
        if cosine <= 0.5:
            similarity_pdf = 0.0
        else:
            similarity_pdf = cosine
        probability *= similarity_pdf

    # Return a weight object

    result.probability = probability
    result.distance = distance
    result.cosine = cosine
    result.critics_pic = critics_pic

    return result


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
    bar_index = bar_idx_map[last_loc_name]
    last_loc_array = [var for idx, var in corpus_lsi_tfidf[bar_index]]

    #last_loc_array = lsa.get_svd_document_vector(last_loc_name)
    user_array = numpy.array(user_vector)

    #return list(last_loc_array)
    
    beta = (.5)**chain_length

    if accepted:
        user_array = user_array + beta*(last_loc_array - user_array)
    else:
        user_array = user_array - beta*(last_loc_array - user_array)

    return list(user_array)


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


if __name__ == '__main__':
    # Bind to PORT if defined, otherwise default to 5000.
    port = int(os.environ.get('PORT', 5000))
    app.debug = True
    #app.run(host='192.168.1.5', port=8001)
    app.run(host='0.0.0.0', port=port)



"""
{'foursquare': {'distance_to_nymag': 0, u'location': {u'city': u'', u'distance': 44, u'country': u'United States', u'lat': 40.748041, u'state': u'NY', u'crossStreet': u'', u'address': u'', u'postalCode': u'', u'lng': -73.987197}, u'id': u'4e7d3b8bb8f724f0c24f3f7d', u'categories': [{u'shortName': u'Karaoke', u'pluralName': u'Karaoke Bars', u'id': u'4bf58dd8d48988d120941735', u'icon': {u'prefix': u'https://foursquare.com/img/categories/nightlife/karaoke_', u'name': u'.png', u'sizes': [32, 44, 64, 88, 256]}, u'name': u'Karaoke Bar'}], u'name': u'32 Karaoke'}, u'_id': ObjectId('51043ce2d08ce64b3c2f64a6'), u'nymag': {u'average_score': None, u'user_review_url': u'?map_view=1&N=0&No=1&listing_id=75735', u'locality': u'New York', u'url': u'http://nymag.com/listings/bar/32-karaoke/index.html', u'region': u'NY', u'categories': [u'After Hours', u' Karaoke Nights'], u'longitude': -73.987249, u'map_url': u'javascript:void(null)', u'postal_code': u'10001', u'best': None, u'address': u'2 W. 32nd St.', u'latitude': 40.747639, u'critics_pic': False, u'desc_short': u'See the profile of this NYC bar at 2 W. 32nd St. in Manhattan.', u'review': u'Have a BYOB sing-along (till 5 a.m.) without the weekend throngs of students.', u'street_address': u'2 W. 32nd St.', u'name': u'32 Karaoke'}}
"""

