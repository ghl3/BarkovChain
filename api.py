
import os
import foursquare


# idea: scrape nymag:
# http://nymag.com/listings/bar/n/

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
    api = foursquare.Foursquare(client_id=client_id,
                                   client_secret=client_secret,
                                   redirect_uri='http://fondu.com/oauth/authorize')
    return api


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

    api = get_api()
    auth_uri = api.oauth.auth_url()


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
    params['limit'] = 50
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
