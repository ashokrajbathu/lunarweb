import os
import jwt, json
from eve import Eve
from flask import Flask, make_response, g, request, jsonify, Response
from eve.auth import TokenAuth
from datetime import datetime, timedelta
from functools import wraps
from settings import TOKEN_SECRET
from bson.objectid import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash
from bson import json_util
from framework.match_me_algorithm import *
import requests
#import grequests
import flask
import urllib2, random
from views import get_search
from weberdb import WeberDB

class TokenAuth(TokenAuth):
	def check_auth(self, token, allowed_roles, resource, method):
		accounts = app.data.driver.db['people']
		return accounts.find_one({'token': token})


app = Eve(__name__,static_url_path='/static')
app.debug = True,

def create_token(user):
    payload = {
        'sub': str(user['_id']),
        'iat': datetime.now(),
        'exp': datetime.now() + timedelta(days=14)
    }

    token = jwt.encode(payload, TOKEN_SECRET)
    return token.decode('unicode_escape')


def parse_token(req):
    token = req.headers.get('Authorization').split()[1]
    return jwt.decode(token, TOKEN_SECRET)


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not request.headers.get('Authorization'):
            response = jsonify(error='Missing authorization header')
            response.status_code = 401
            return response

        payload = parse_token(request)

        if datetime.fromtimestamp(payload['exp']) < datetime.now():
            response = jsonify(error='Token has expired')
            response.status_code = 401
            return response

        g.user_id = payload['sub']

        return f(*args, **kwargs)

    return decorated_function

# Routes

@app.route('/')
def index():
	return make_response(open('static/app/index.html').read())


@app.route('/api/me')
@login_required
def me():
	return Response(json.dumps(g.user_id),  mimetype='application/json')

@app.route('/foo/<path:filename>')
def send_foo(filename):
    return send_from_directory('/static/', filename)

@app.route('/auth/login', methods=['POST'])
def login():
    accounts = app.data.driver.db['people']
    user = accounts.find_one({'email': request.json['email']})
    if not user or not check_password_hash(user['password'], request.json['password']):
        response = jsonify(error='Wrong Email or Password')
        response.status_code = 401
        return response
    #return json.dumps(user,default=json_util.default)
    token = create_token(user)
    return jsonify(token=token)

@app.route('/getsearch')
def getSearchResults():
    extract_words = []
    extract_words = create_tokens(request.args.get("searchtext"))
    print len(extract_words)
    if len(extract_words) == 2:
        data = 'http://127.0.0.1:8000/api/posts?where={"keywords":{"$in":'+json.dumps(list(extract_words))+'}}'
        r = requests.get(data)
        return r.data
    else:
        return "none"

@app.route('/similarwords')
def getSimilarWords():
    words = parse_sentence(request.args.get("new_post"))
    post_tokens = create_tokens(request.args.get("new_post"))
    keywords = set(list(post_tokens)+list(words))
    return json.dumps(list(set(keywords)))

@app.route('/auth/signup', methods=['POST'])
def signup():
		accounts = app.data.driver.db['people']
		user = {
				'email' :request.json['email'],
				'password' :generate_password_hash(request.json['password'])
		}
		accounts.insert(user)
		token = create_token(user)
		return jsonify(token=token)

friendsNotific = 0
searchNotific = 0

def check_updates():

    global friendsNotific, searchNotific

    if(searchNotific):
        print 'yessssssss'
        data = json.dumps({'friendsnotific':friendsNotific,'searchNotific':searchNotific})
        yield 'data: %s \n\n' % data
        searchNotific = 0
    if(friendsNotific):
        print 'noooooooooooo'
        data = json.dumps({'friendsnotific':friendsNotific,'searchNotific':searchNotific})
        yield 'data: %s \n\n' % data
        friendsNotific = 0

@app.route('/stream')
#@nocache
def stream():
    return Response(check_updates(),mimetype='text/event-stream')

def after_post_inserted(items):
    for atribute,value in items[0].iteritems():
        if(atribute == "keywords"):
            db = WeberDB()
            isUpdated =  db.update_search(value,items[0]['_id'])
            if(isUpdated['nModified'] >= 1):
                global searchNotific
                searchNotific = 1


def after_friend_notification_get(updates, original):
    print 'hhhhhhhhhhhhhhhhhhhhh'
    global friendsNotific
    friendsNotific = 1


app.on_inserted_people_posts+= after_post_inserted
app.on_updated_people+= after_friend_notification_get

app.run(host='localhost',port=8000)
