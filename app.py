#!/usr/bin/env python

import os
import random
import math

import json
from flask import Flask
from flask import render_template
from flask import request
from flask import jsonify
from flask import Response
from bson import json_util

#import unicodedata

from database import connect_to_database
from database import valid_entry_dict

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

@app.route('/api/locations')
def api_locations( methods=['GET']):
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
        return not_found()

    # Check validity of body
    print "Request Args: ", request.args
    required_args = ['longitude', 'latitude', 'number_of_locations']
    for arg in required_args:
        if arg not in request.args:
            print "Didn't find: %s" % arg
            return invalid_content

    # Generate and return the response
    position = {'longitude' : float(request.args['longitude']),
                'latitude' : float(request.args['latitude'])}

    number_of_locations = int(request.args['number_of_locations'])
    locations = get_close_locations(position=position, 
                                    number_of_locations=number_of_locations)
    print "Nearest Locations:"
    print locations

    data_for_app = [location['nymag'] for location in locations]

    js = json.dumps(data_for_app, default=json_util.default)
    resp = Response(js, status=200, mimetype='application/json')
    #resp.headers['Link'] = 'http://luisrei.com'

    return resp


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


def get_close_locations(position, number_of_locations=3):
    """
    Return 'number_of_locations' locations that are
    'close' to the given position, where the position
    is a dictionary of 'longitude' and 'latitude'

    Note: 1 New York Block is approximately:
    delta-latitude = 0.0003
    delta-longitude = 0.001

    Return a list
    """
    
    # New York Block dimensions
    block_lat = 0.0003
    block_lon = 0.001

    # Block "distance" = 5
    # ie, we want a restaurant within 5 blocks
    block_distance = 10

    lat, lon = position['latitude'], position['longitude']

    lat_min = lat - block_distance*block_lat
    lat_max = lat + block_distance*block_lat
    lon_min = lon - block_distance*block_lon
    lon_max = lon + block_distance*block_lon

    db_query = {
        "nymag.latitude": {"$gt": lat_min, "$lt": lat_max},
        "nymag.longitude": {"$gt": lon_min, "$lt": lon_max}
        }

    #db_query = {}
    # Ensure the query is valid
    db_query.update(valid_entry_dict())

    print "db query: ", db_query

    db, connection = connect_to_database(table_name="barkov_chain")
    bars = db['bars']
    locations = bars.find(db_query)
    
    # Here, we would do some magic to pick
    # out the 'best' locations
    nearest_locations = []
    for location in locations:
        nymag = location['nymag']
        distance = distance_dr(lat, lon,
                               nymag['latitude'], 
                               nymag['longitude'])
        nearest_locations.append( (location, distance) )

    nearest_locations.sort(key=lambda x: x[1])

    return [location[0] for location in nearest_locations[:number_of_locations]]

    #for location in locations:
    #    print location
    #return list(locations)


def distance_dr(lat0, lon0, lat1, lon1):
    d2 = (lat0-lat1)*(lat0-lat1) + (lon0-lon1)*(lon0-lon1)
    return math.sqrt(d2)


def create_static_map_src(locations, path_color = '0x0000ff', 
                          path_weight=5):
    """
    Create a static google map based on 
    the list of venues.

    Each venue is a dict that contains
    "latitude" and "longitude".

    Return an image string to be put as the 'src'
    of an html image tag.
    """

    colors = ["red", "green", "blue", "orange", "purple", "yellow"]

    points = []
    for venue, color in zip(locations, colors):
        points.append((venue['latitude'], venue['longitude'], color))

    image_src = 'http://maps.googleapis.com/maps/api/staticmap'
    image_src += '?center=Washington+Square+Park,New+York,NY'
    image_src += '&zoom=12'
    image_src += '&size=500x700'
    image_src += '&maptype=roadmap'
    image_src += ''

    for (lat, lon, color) in points:
        image_src += '&markers=color:{color}%7Clabel:S%7C{lat},{lon}' \
            .format(lat=lat, lon=lon, color=color)

    image_src += '&sensor=false'
    image_src += '&path=color:{path_color}|weight:{path_weight}' \
        .format(path_color=path_color, path_weight=path_weight)

    for (lat, lon, color) in points:
        image_src += '|{lat},{lon}'.format(lat=lat, lon=lon)
    image_src += '&'

    return image_src

# &markers=color:green%7Clabel:G%7C40.711614,-74.012318&markers=color:red%7Ccolor:red%7Clabel:C%7C40.718217,-73.998284&sensor=false&path=color:0x0000ff|weight:5|40.702147,-74.015794|40.711614,-74.012318|40.718217,-73.998284&
    
if __name__ == '__main__':
    # Bind to PORT if defined, otherwise default to 5000.
    port = int(os.environ.get('PORT', 5000))
    app.debug = True
    app.run(host='0.0.0.0', port=port)
    

