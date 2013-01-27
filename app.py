#!/usr/bin/env python

import os
import random

from flask import Flask
from flask import render_template
from flask import request
from flask import jsonify

from nymag_scrape import connect_to_database

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

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


def get_random_locations(num_locations=3):
    """
    Return 3 random locations from the database
    """
    
    db, connection = connect_to_database(table_name="barkov_chain")
    nymag = db['nymag']
    locations = nymag.find({ 'review' : {'$exists':True} },
                         limit = 100)
    locations = [locations[random.randint(0, 100)] for i in range(num_locations)]
    return locations


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
    

