#!/usr/bin/python

import flask
import bcrypt
import boto3
import botocore
import functools
import jwt
import time
import requests

application = flask.Flask(__name__)

# The secret key should really be read from something like DynamoDB
# or an s3 bucket in an encrypted format, and then use KMS to decrypt
# it
application.config['SECRET_KEY'] = ''
application.config['EXPIRE'] = 3600

ERR_UNKNOWN = 100
ERR_KEY_NOT_EXIST = 200
ERR_BAD_REQUEST = 300
ERR_UNAUTHORIZED = 400
ERR_TOKEN_EXPIRED = 500
ERR_KEY_EXISTS = 600

with application.app_context():
    resp = requests.get(
        'http://169.254.169.254/latest/meta-data/placement/availability-zone'
    )
    region = resp.content[:-1]
    s3 = boto3.client('s3')
    ssm = boto3.client('ssm', region_name=region)
    response = ssm.get_parameters(
        Names=['storserv-jwt'],
        WithDecryption=True
    )
    application.config['SECRET_KEY'] = response['Parameters'][0]['Value']


def message(**kwargs):
    msg = {}
    for k, v in kwargs.iteritems():
        if isinstance(v, str):
            v = v.decode('utf-8')
        msg[k] = v
    return flask.jsonify(msg)


def error(msg, error_code, **kwargs):
    return message(message=msg, error=error_code, **kwargs)


def jwtrequired(fn):
    '''
    This is a decorator for verifying the JWT tokens and unpacking the payload
    '''
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        if 'Authorization' in flask.request.headers:
            try:
                token = flask.request.headers['Authorization'].split()
                payload = jwt.decode(token[1], application.config['SECRET_KEY'])
            except jwt.DecodeError as e:
                return error("Unable to decode JWT: {0}".format(e), ERR_UNKNOWN)
            except jwt.ExpiredSignatureError:
                return error('Token is expired', ERR_TOKEN_EXPIRED)
            flask.request._bucket = payload['buk']
        else:
            return error("Unauthorized", ERR_UNAUTHORIZED)
        return fn(*args, **kwargs)
    return wrapper


def obj_exists(bucket, key):
    try:
        s3.head_object(Bucket=bucket, Key=key)
        return True
    except botocore.exceptions.ClientError:
        return False


@application.route("/v1/data/", methods=["GET"])
@jwtrequired
def get_root():
    return get('/')


@application.route("/v1/data/<path:key>", methods=["GET"])
@jwtrequired
def get(key):
    '''
    Retrieves a key's value
    '''
    if key.endswith('/'):
        # A little bit of a hack to allow for listing the root directory
        if key == '/':
            key = ''
        objects = s3.list_objects_v2(Bucket=flask.request._bucket, Prefix=key, Delimiter='/')
        keys = []
        if 'Contents' in objects:
            for o in objects['Contents']:
                keys.append(o['Key'])
        if 'CommonPrefixes' in objects:
            for o in objects['CommonPrefixes']:
                keys.append(o['Prefix'])
        return message(keys=keys)
    if obj_exists(flask.request._bucket, key):
        val = s3.get_object(Bucket=flask.request._bucket, Key=key)
        return message(key=key, value=val['Body'].read())
    else:
        return error('Key {0} not found'.format(key), ERR_KEY_NOT_EXIST)


@application.route("/v1/data/<path:key>", methods=["PUT"])
@jwtrequired
def edit(key):
    '''
    Updates a key's value
    '''
    if 'value' in flask.request.form:
        val = flask.request.form['value']
    else:
        val = ''
    try:
        s3.put_object(Bucket=flask.request._bucket, Key=key, Body=val.decode('utf-8'))
    except Exception as e:
        return error('Could not update key {0}'.format(e), ERR_UNKNOWN, key=key)
    return message(key=key, value=val)


@application.route("/v1/data/<path:key>", methods=["POST"])
@jwtrequired
def new(key):
    '''
    Inserts a new key into the user's bucket
    '''
    if obj_exists(flask.request._bucket, key):
        return error('Key {0} already exists'.format(key), ERR_KEY_EXISTS)

    if 'value' in flask.request.form:
        val = flask.request.form['value']
    else:
        val = ''
    try:
        s3.put_object(Bucket=flask.request._bucket, Key=key, Body=val.decode('utf-8'))
    except Exception as e:
        return error('Could not create key: {0}'.format(e), ERR_UNKNOWN, key=key)
    return message(key=key, value=val)


@application.route("/v1/data/<path:key>", methods=["DELETE"])
@jwtrequired
def delete(key):
    '''
    Deletes a key from the user's bucket
    '''
    if not obj_exists(flask.request._bucket, key):
        return error('Key not found', ERR_KEY_NOT_EXIST, key=key)

    try:
        s3.delete_object(Bucket=flask.request._bucket, Key=key)
    except Exception as e:
        return error('Unable to remove key: {0}'.format(e), ERR_UNKNOWN, key=key)
    return message(message='Deleted key', key=key)


@application.route("/v1/login", methods=["POST"])
def login():
    '''
    Authenticates the username and password of a user by comparing it to the bcrypt'd
    hash in the pre-defined user bucket.

    It then generates a JWT token based off the username and password.
    The payload of the JWT includes the name of the bucket for the user's keys
    '''

    if 'username' in flask.request.form and 'password' in flask.request.form:
        user = flask.request.form['username']
        password = flask.request.form['password']
        try:
            s3.head_object(Bucket='storserv-users', Key=user)
        except botocore.exceptions.ClientError:
            return error('Invalid username or password', ERR_UNAUTHORIZED)

        # Because s3 buckets are global domain names, there's some worry about
        # collisions with the namespace for users.  Could enhance this storing a
        # user config in the user key, rather than simply the pw hash.  The bucket
        # name could then be obtained by that and it could be randomly generated,
        # which would have less of a chance of a collision.

        pwhash = s3.get_object(Bucket='storserv-users', Key=user)
        if bcrypt.checkpw(password, pwhash['Body'].read()):
            payload = {
                'buk': 'storserv-{0}'.format(user),
                'exp': time.time() + application.config['EXPIRE']
            }
            token = jwt.encode(payload, application.config['SECRET_KEY'], algorithm='HS256')
            return flask.jsonify({'jwt': token})
        else:
            return error('Invalid username or password', ERR_UNAUTHORIZED)
    else:
        return error('You must specify a username and a password', ERR_BAD_REQUEST)


@application.route("/v1/ping", methods=["GET"])
def ping():
    return "pong"


if __name__ == "__main__":
    application.run(host='0.0.0.0', port='80')
