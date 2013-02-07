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
    lsi_index, bar_idx_map, idx_bar_map = load_lsi('data')

app = Flask(__name__)

# Connect to the db
mongo_db, mongo_connection = connect_to_database(table_name="barkov_chain")

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
    bar_index = bar_idx_map[next_location['nymag']['name']]
    initial_user_vector = [var for idx, var in corpus_lsi_tfidf[bar_index]]
    print "Created Initial User Vector: ", 
    print initial_user_vector

    # Return the data
    data_for_app = format_location(next_location, initial_user_vector)
    resp = Response(data_for_app, status=200, mimetype='application/json')
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
    print "Updating User Vector"
    user_vector = update_user_vector(user_vector, last_venue, 
                                     accepted, len(current_chain))

    # Get the next location, package it up
    # and send it to the client
    print "Getting Next Location"
    next_location = get_next_location(current_chain, rejected_locations, user_vector)

    print "Formatting Location Dict"
    data_for_app = format_location(next_location, user_vector)

    print "Creating Response"
    resp = Response(data_for_app, status=200, mimetype='application/json')

    print "Done fetching next location"
    print "\n"
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

def format_location(db_entry, user_vector):
    """
    Convert a db entry and a user vector
    into the JSON to be sent to the app.
    """
    data_for_app = {}
    data_for_app['location'] = {}
    data_for_app['location']['name'] = db_entry['nymag']['name']
    data_for_app['location']['longitude'] = db_entry['nymag']['longitude']
    data_for_app['location']['latitude'] = db_entry['nymag']['latitude']
    data_for_app['location']['_id'] = str(db_entry['_id'])
    data_for_app['location']['nymag'] = db_entry['nymag']
    data_for_app['location']['foursquare'] = db_entry['foursquare']
    data_for_app['user_vector'] = user_vector

    data_json = json.dumps(data_for_app, default=json_util.default)

    return data_json


class weight(object):
    
    def __init__(self):
        self.probability = None
        self.distance = None
        self.pdf_distance = None
        self.cosine = None
        self.pdf_cosine = None
        self.critics_pic = None
        self.words = None

    def __repr__(self):
        repr_str = ''
        repr_str += "Probability = %.5s " % self.probability
        repr_str += "("
        repr_str += "Distance: pdf[%.5s m] = %.7s, " % (self.distance, self.pdf_distance)
        repr_str += "Cosine: pdf[%.7s] = %.7s, " % (self.cosine, self.pdf_cosine)
        repr_str += "Critics Pic: %s" % self.critics_pic
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
        "nymag.latitude": {'$exists':True, "$gt": lat_min, "$lt": lat_max},
        "nymag.longitude": {'$exists':True, "$gt": lon_min, "$lt": lon_max}
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
    print "Fetching Locations"
    bars = mongo_db['bars2']
    db_return = bars.find(db_query)

    print "Found Nearby Locations: ", 
    proposed_locations = list(db_return)
    print [location['nymag']['name'] for location in proposed_locations]

    # If we didn't grab enough locations,
    # try a larger search block
    print "Getting Total Probability"
    total_probability = 0.0
    for location in proposed_locations:
        weight_result = mc_weight(location, current_location, user_vector)
        total_probability += weight_result.probability

    while (len(proposed_locations) < 5 or total_probability <= 0.000001):
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
    print "Running MC"
    mc_steps = 0
    while True:
        mc_steps += 1
        if mc_steps % 1000 == 0:
            print "MC Step: ", mc_steps
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


def mc_weight(proposed, current, user_vector):
    """ 
    Calculate the probability of jumping from current to proposed
    """

    result = weight()
    result.probability = 1.0

    name = proposed['nymag']['name']
    initial = current.get('initial', False)

    #
    # To Do: favor linear paths
    #
    result.distance = distance_dr(proposed['nymag'], current)
    result.pdf_distance = scipy.stats.expon.pdf(result.distance, scale=300) # size is 100 meters
    result.probability *= result.pdf_distance

    # Disfavor non critics-picks
    result.critics_pic = False
    if proposed['nymag'].get(u'critics_pic', False):
        result.critics_pic = True
    else:
        result.probability *= .5
        
    # Get the lsa cosine, but only if this isn't
    # the initial marker
    result.cosine = None
    if not initial:
        try:
            # User vector lives in the lsa[tfidf] space
            user_array = numpy.array(user_vector)
            sims = lsi_index[user_array]
            proposed_bar_idx = bar_idx_map[name]
            result.cosine = sims[proposed_bar_idx]
            result.words = [dictionary[pair[0]] for pair in corpus[proposed_bar_idx]]
        except:
            print "Cosine Error"
            raise

        # We here directly use the cosine as the pdf, but one
        # could be smarter about this
        # similarity_pdf = scipy.stats.expon.pdf(cosine+1.0, scale=0.001)
        result.pdf_cosine = (result.cosine+1.0)/(2.0)*(result.cosine+1.0)/(2.0)
        #if cosine <= 0.5:
        #    similarity_pdf = 0.0
        #else:
        #    similarity_pdf = cosine
        result.probability *= result.pdf_cosine

    # Return a weight object
    #result.probability = probability
    #result.distance = distance
    #result.cosine = cosine
    #result.critics_pic = critics_pic

    return result


def update_user_vector(user_vector, last_location, 
                       accepted, chain_length):
    """
    Update the user's vector 
    based on whether he accepted the last location
    The size of the update is based on how many 
    entries in the chain that we've had so far
    """

    print "Updating User Vector"
    print "Current Vector: ", user_vector
    print "Accepted last location: %s:" % accepted, last_location

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

    print "Updated Vector: ", user_array

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
    port = int(os.environ.get('PORT', 8000))
    app.debug = True
    #app.run(host='192.168.1.5', port=8001)
    app.run(host='0.0.0.0', port=port)
