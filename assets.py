
import argparse

from os import listdir
from os.path import isfile
from os.path import isdir

import boto
from boto.s3.key import Key


def deploy_assets():
    """
    Send all assets in the 'assets' directory
    to the s3 bucket 'barkov_chain'
    """
    try:
        s3 = boto.connect_s3()
    except boto.exception.NoAuthHandlerFound:
        print "Cannot deploy.  Ensure that authentication environment variables exist"
        return
        
    bucket = s3.get_bucket('barkov_chain')

    if not isdir('assets'):
        print "Error: assets directory doesn't exist"
        return

    for f in listdir('assets'):
        if f.startswith('.'): 
            continue
        print "Deploying assets/%s to s3" % f
        k = Key(bucket)
        k.key = f
        k.set_contents_from_filename('assets/' + f)


def gather_assets():
    """
    Gather all assets from the amazon s3
    bucket 'barkov_chain' and download 
    those that don't exist locally.
    """

    try:
        s3 = boto.connect_s3()
    except boto.exception.NoAuthHandlerFound:
        print "Using local assets"
        return


    bucket = s3.get_bucket('barkov_chain')

    if not isdir('assets'):
        print "Error: assets directory doesn't exist"
        return

    for key in bucket.list():
        key_name = key.name
        if key_name.startswith('.'): 
            continue
        file_name = 'assets/' + key_name
        if isfile(file_name): 
            print "gather_assets: Not downloading %s, file already exists" % file_name
            continue
        else:
            print "Downloading file %s to %s" % (key_name, file_name)
            key.get_contents_to_filename(file_name)


def main():

    parser = argparse.ArgumentParser(description='Deploy or gather assets from Amazon s3')
    parser.add_argument('--deploy', '-d', dest='deploy', action="store_true", default=False,
                        help='Deploy all assets to s3')
    parser.add_argument('--gather', '-g', dest='gather', action="store_true", default=False,
                        help='Gather assets from s3')
    args = parser.parse_args()

    if args.deploy: 
        deploy_assets()

    if args.gather: 
        gather_assets()

if __name__ == "__main__":
    main()
