
import os
import foursquare


def get_credentials():
    """ 
    Query the environment to get
    the API KEY and SECRET for LASTFM
    """

    CLIENT_ID = os.environ["FOURSQUARE_CLIENT_ID"]
    CLIENT_SECRET = os.environ["FOURSQUARE_CLIENT_SECRET"]

    return (CLIENT_ID, CLIENT_SECRET)


def get_api():
    
    client_id, client_secret = get_credentials()
    api = foursquare.Foursquare(client_id=client_id,
                                   client_secret=client_secret,
                                   redirect_uri='http://fondu.com/oauth/authorize')
    return api


def main():

    client = get_api()
    auth_uri = client.oauth.auth_url()

    #print auth_uri
    #print client.users('1183247')
    #print client.venues('40a55d80f964a52020f31ee3')
    params = {}
    params['query'] = 'coffee'
    params['near'] = 'New York'
    params['intent'] = 'browse'
    #response = client.venues.search(params={'near': 'New York', 'query':'coffee'})
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
