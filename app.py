#!/usr/bin/env python

import os
import random
import math
import json
import random

from flask import Flask
from flask import render_template
from flask import request
from flask import jsonify
from flask import Response
from bson import json_util

from database import connect_to_database
from database import valid_entry_dict

import geopy
import geopy.distance

import scipy.stats


app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/bootstrap')
def bootstrap():
    return render_template('bootstrap.html')

@app.route('/map')
def map():
    locations = get_random_locations()
    for venue in locations:
        print venue
        print venue['name']
        print venue['address']
        print venue['desc_short']
    img_src = create_static_map_src(locations)
    return render_template('map.html',
                           venue_list=locations,
                           img_src=img_src)

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

@app.route('/api/locations', methods=['POST'] )
def api_locations():
    """
    Get locations and return as JSON
    Requires the following parameters:

    { 'position' : {
             'longitude' : longitude,
             'latitude' : latitude,
             },
      'number_of_locations' : number_of_locations
    }
    
    """
    # Check content type (only json for now)
    # Be tolerent when recieving, 
    # be string when sending
    if 'json' not in request.headers['Content-Type']:
        print "Bad Content-Type : Expected JSON"
        return not_found()
    print "Content Type is okay"

    # Check validity of body
    #print "Request Args: ", request.args, ''
    #required_args = ['longitude', 'latitude', 'number_of_locations']
    #for arg in required_args:
    #    if arg not in request.args:
    #        print "Didn't find: %s" % arg
    #        return invalid_content
    #print "Chain: ", request.args['chain'], ''

    '''
    json_data = json.loads(request.data)
    print request.form
    print request.json
    '''

    """
    print request.method
    data = json.loads(request.data)
    print data
    print request.data
    print request.data['chain']
    print "About to check form"
    print request.form
    print request.form.get('chain', "None")
    print "Successfully checked form"
    """

    current_chain = request.json['chain']
    current_location = current_chain[-1]

    # Generate and return the response
    #current_location = {'longitude' : float(request.args['longitude']),
    #                    'latitude' : float(request.args['latitude'])}
    next_location = get_next_location(current_location)
    data_for_app = next_location['nymag']

    js = json.dumps(data_for_app, default=json_util.default)
    resp = Response(js, status=200, mimetype='application/json')
    #resp.headers['Link'] = 'http://luisrei.com'
    return resp


def get_lat_lon_square_query(current_location, blocks=10):
    """
    Return the min/max of lat and lon
    to be used in the query's bounding box.
    """

    lat, lon = current_location['latitude'], current_location['longitude']
    
    # New York Block dimensions
    block_lat = 0.0003
    block_lon = 0.001

    # Block "distance" = 5
    # ie, we want a restaurant within 5 blocks
    block_distance = 10

    lat_min = lat - block_distance*block_lat
    lat_max = lat + block_distance*block_lat
    lon_min = lon - block_distance*block_lon
    lon_max = lon + block_distance*block_lon

    query = {
        "nymag.latitude": {"$gt": lat_min, "$lt": lat_max},
        "nymag.longitude": {"$gt": lon_min, "$lt": lon_max}
        }

    #return (lat_min, lat_max), (lon_min, lon_max)
    return query

def get_next_location(current_location):
    """
    Return the next location based on the current markov chain.

    'current_chain' is a list of location dictionaries that
    was sent from the javascript GET request

    We return a single dictionary containing the information
    about the next location.

    Return a list
    """

    # Get the position bounding box for the query
    #
    #(lat_min, lat_max), (lon_min, lon_max) = get_lat_lon_square(lat, lon, blocks=10)

    # Build the db query
    blocks=10
    db_query = {}
    #db_query.update()
    db_query.update(get_lat_lon_square_query(current_location, blocks=blocks))
    db_query.update(valid_entry_dict())

    # Get the nearby locations
    db, connection = connect_to_database(table_name="barkov_chain")
    bars = db['bars']
    locations = list(bars.find(db_query))

    # If we didn't grab enough locations,
    # try a larger search block
    while len(locations) < 5:
        print "Too few nearby locations found within %s blocks (%s). Extending query" % (blocks, len(locations))
        blocks += 10
        updated_distance = get_lat_lon_square_query(current_location, blocks=blocks)
        for key, val in updated_distance.iteritems():
            db_query[key] = val
        print db_query
        locations = list(bars.find(db_query))

    # Select the next location in the chain
    next_location = next_location_from_mc(locations, current_location)

    return next_location


def next_location_from_mc(locations, current_location):
    """
    Here, we implement the markov chain and pick the next location.

    We simply get the probability of transition and throw
    a random number betwen 0 and 1 to determine if we
    accept it or not.
    """

    # Calculate the weight function
    while True:
        proposed = random.choice(locations)
        probability = mc_weight(proposed, current_location)
        mc_throw = random.uniform(0.0, 1.0)
        print "throw %s" % mc_throw
        if probability > mc_throw:
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


def mc_weight(proposed, current):
    """ 
    Calculate the probability of jumping from current to proposed
    """

    probability = 1.0

    distance = distance_dr(proposed['nymag'], current)
    distance_pdf = scipy.stats.expon.pdf(distance, scale=200) # size is 100 meters
    probability *= distance_pdf

    # Disfavor non critics-picks
    if proposed['nymag'].get(u'critics_pic', False) != True:
        probability *= .1


    """
{'foursquare': {'distance_to_nymag': 0, u'location': {u'city': u'', u'distance': 44, u'country': u'United States', u'lat': 40.748041, u'state': u'NY', u'crossStreet': u'', u'address': u'', u'postalCode': u'', u'lng': -73.987197}, u'id': u'4e7d3b8bb8f724f0c24f3f7d', u'categories': [{u'shortName': u'Karaoke', u'pluralName': u'Karaoke Bars', u'id': u'4bf58dd8d48988d120941735', u'icon': {u'prefix': u'https://foursquare.com/img/categories/nightlife/karaoke_', u'name': u'.png', u'sizes': [32, 44, 64, 88, 256]}, u'name': u'Karaoke Bar'}], u'name': u'32 Karaoke'}, u'_id': ObjectId('51043ce2d08ce64b3c2f64a6'), u'nymag': {u'average_score': None, u'user_review_url': u'?map_view=1&N=0&No=1&listing_id=75735', u'locality': u'New York', u'url': u'http://nymag.com/listings/bar/32-karaoke/index.html', u'region': u'NY', u'categories': [u'After Hours', u' Karaoke Nights'], u'longitude': -73.987249, u'map_url': u'javascript:void(null)', u'postal_code': u'10001', u'best': None, u'address': u'2 W. 32nd St.', u'latitude': 40.747639, u'critics_pic': False, u'desc_short': u'See the profile of this NYC bar at 2 W. 32nd St. in Manhattan.', u'review': u'Have a BYOB sing-along (till 5 a.m.) without the weekend throngs of students.', u'street_address': u'2 W. 32nd St.', u'name': u'32 Karaoke'}}
    """
    

    #print "Monte Carlo: distance %s probability %s" % (distance, probability),

    return probability


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
    app.run(host='0.0.0.0', port=port)
