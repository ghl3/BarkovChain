#!/usr/bin/env python

from __future__ import division

import os
import random
import math
import json
import random
from math import pi
from math import tan                
import scipy.stats

from flask import Flask
from flask import render_template
from flask import request
from flask import jsonify
from flask import Response
from bson import json_util
from bson import ObjectId

from database import connect_to_database
from database import valid_entry_dict
from database import acceptable_location

import geopy
import geopy.distance

from semantic import load_corpus, load_lsi, cosine
from semantic import update_vector, important_words

from assets import gather_assets

# If necessary, download the trained
# model from Amazon S3
gather_assets()

# Load the semantic models
dictionary, corpus, tfidf, bar_idx_map, idx_bar_map = load_corpus()
lsi, corpus_lsi_tfidf, lsi_index = load_lsi()

# Connect to the db
mongo_db, mongo_connection = connect_to_database(table_name="barkov_chain")

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/slides')
def slides():
    return render_template('slides.html')

@app.route('/api/initial_location', methods=['POST'] )
def api_initial_location():
    """
    Take lat/lon coordinates and return
    the initial location, as well as the
    initial user vector.

    Input:
    {'location' : {'latitude' : lat, 'longitude' : lon}}

    Returns:
    { 'location' : { 'name' : ..., 
                     'longitude' : ..., 
                     'latitude' : ..., 
                     '_id' : ..., 
                     'nymag' : {}, 
                     'foursquare' : {} } }
    """

    if 'json' not in request.headers['Content-Type']:
        print "Bad Content-Type : Expected JSON"
        return not_found()

    print "Getting Initial Location"
    marker_location = request.json['location']
    marker_location['initial'] = True
    current_chain = [marker_location]
    next_location = get_next_location(current_chain, history=[])

    print "Returning Data"
    data_for_app = format_location(next_location)
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

    Input:
    { 'chain' : [...],
      'history' [...] }

    Returns:
    { 'location' : { 'name' : ..., 
                     'longitude' : ..., 
                     'latitude' : ..., 
                     '_id' : ..., 
                     'nymag' : {}, 
                     'foursquare' : {} } }
    """

    if 'json' not in request.headers['Content-Type']:
        print "Bad Content-Type : Expected JSON"
        return not_found()

    current_chain = request.json['chain']
    history = request.json['history']

    print "Getting Next Location"
    next_location = get_next_location(current_chain, history=history)

    print "Formatting Location Dict"
    data_for_app = format_location(next_location)

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


def sigmoid(x):
    """ Return the sigmoid function"""
    return 1 / (1 + math.exp(-x))


def format_location(db_entry):
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

    data_json = json.dumps(data_for_app, default=json_util.default)

    return data_json


class weight(object):
    """
    An object to hold a locations transition weight
    
    - probability: The total transition probability
    - distance: The spacial distance to this location
    - pdf_distance: The pdf of the spacial distance
    - cosine: A list of semantic cosines to this location
    - pdf_cosine: The pdf associated with the semantic cosines
    - critics_pick: If this location is well reviewed
    """
    
    def __init__(self):
        self.probability = None
        self.distance = None
        self.pdf_distance = None
        #self.cosine = None
        self.cosines_to_good = []
        self.cosines_to_bad = []
        self.pdf_cosine = None
        self.critics_pic = None

    def __repr__(self):
        repr_str = ''
        repr_str += "Probability = %.5s " % self.probability
        repr_str += "("
        repr_str += "Distance: pdf[%.5s m] = %.7s, " % (self.distance, self.pdf_distance)
        repr_str += "Cosine: pdf[("
        for csn in self.cosines_to_good:
            repr_str += "%.4s," % csn
        repr_str += "), ("
        for csn in self.cosines_to_bad:
            repr_str += "%.4s," % csn
        repr_str += ") = %.7s," % self.pdf_cosine
        repr_str += "Critics Pic: %s" % self.critics_pic
        repr_str += ")"
        return repr_str


def get_lat_lon_square_query(current_location, blocks):
    """
    Return the db query specifying the 
    min/max of lat and lon bounding box
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


def get_proposed_locations(collection, query):
    """
    Query the database and return a list
    of acceptable locations
    """
    db_return = collection.find(query)
    proposed_locations = list(db_return)
    return [location for location in proposed_locations
            if acceptable_location(location)]
    

def get_next_location(current_chain, history):
    """
    Return the next location 

    Based on:
     - The current location
     - The user's history of accepts and rejects

    Do not return a location that the user has already seen

    Return a dictionary describing the 'next' location
    """

    current_location = current_chain[-1]
    used_ids = [ObjectId(location['venue']['_id']) for location in history]
    bars = mongo_db['bars']

    # Build the db query
    blocks=10
    db_query = {}
    db_query.update(get_lat_lon_square_query(current_location, blocks=blocks))
    db_query.update(valid_entry_dict())
    db_query.update( {'_id' : {'$nin' : used_ids}})

    print "Fetching Locations"
    proposed_locations = get_proposed_locations(bars, db_query)

    # If we didn't grab enough locations,
    # try a larger search block
    while (len(proposed_locations) < 5):
        print "Too few nearby locations found within %s blocks (%s)." \
            % (blocks, len(proposed_locations))
        blocks *= 2
        updated_distance = get_lat_lon_square_query(current_location, blocks=blocks)
        db_query.update(updated_distance)
        proposed_locations = get_proposed_locations(bars, db_query)

    # Get the weights for the nearby locations
    weight_results = {}
    for location in proposed_locations:
        weight_result = mc_weight(location, current_location, history)
        weight_results[location['nymag']['name']] = weight_result

    # Pick the highest weighted locations
    closest = []
    for location in proposed_locations:
        weight_result = weight_results[location['nymag']['name']]
        closest.append((location, weight_result.pdf_cosine, weight_result.probability))
        
    # Sort by pdf(cosine), and then total probability
    # And get the top 5
    closest.sort(key=lambda x: (x[1], x[2]), reverse=True)
    proposed_locations = [location for (location, weight, pdf) in closest][:5]
    print "Closest Locations: "
    print [location['nymag']['name'] for location in proposed_locations]

    # Get the normalization factor
    total_probability = 0.0
    for location in proposed_locations:
        weight_result = weight_results[location['nymag']['name']]
        total_probability += weight_result.probability

    # Calculate the weight function
    print "Running MC"
    mc_steps = 0
    while True:
        mc_steps += 1
        if mc_steps % 1000 == 0:
            print "MC Step: ", mc_steps
        proposed = random.choice(proposed_locations)
        weight_result = weight_results[proposed['nymag']['name']]
        weight_result.probability /= total_probability
        mc_throw = random.uniform(0.0, 1.0)
        if weight_result.probability > mc_throw:
            print "Monte Carlo Converged after %s throws: " % mc_steps,
            print weight_result
            return proposed

    raise Exception("MonteCarloError")


def mc_weight(proposed, current, history):
    """ 
    Calculate the un-normalized transition probability

    Depends on:
    - Distance
    - Reviews ('critics pick')
    - History (if not the first choice)
    """

    result = weight()
    result.probability = 1.0

    name = proposed['nymag']['name']
    initial = False if len(history) > 0 else True

    #
    # To Do: favor linear paths
    #
    result.distance = distance_dr(proposed['nymag'], current)
    result.pdf_distance = scipy.stats.expon.pdf(result.distance, scale=300) # Scale in meters
    result.probability *= result.pdf_distance

    # Disfavor non critics-picks
    result.critics_pic = False
    if proposed['nymag'].get(u'critics_pic', False):
        result.critics_pic = True
    else:
        result.probability *= .5
        
    # Get the lsa cosine if there is a history
    result.pdf_cosine = 1.0 
    if not initial:
        try:

            # Get the index of the proposed bar
            proposed_bar_idx = bar_idx_map[name]   
            proposed_bar_vec = corpus_lsi_tfidf[proposed_bar_idx]

            # User vector lives in the lsa[tfidf] space
            cosines_good = []
            cosines_bad = []
            result.pdf_cosine = 1.0

            for location in history:

                location_name = location['venue']['name']
                bar_index = bar_idx_map[location_name]
                vec = corpus_lsi_tfidf[bar_index]
                csn = cosine(vec, proposed_bar_vec)
                accepted = True if location['accepted'] else False
                print "%s, accepted = %s, cosine = %s" % (location_name, accepted, csn)
                
                if accepted:
                    result.pdf_cosine *= sigmoid(csn)
                    result.cosines_to_good.append(csn)
                else:
                    result.pdf_cosine *= sigmoid(-1*csn)
                    result.cosines_to_bad.append(csn)

        except Exception as e:
            print "Cosine Error"
            print e

        result.probability *= result.pdf_cosine

    return result


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
