import os
import functools
import boto3
from dotenv import load_dotenv

from flask import Flask, request, session, g
from flask_debugtoolbar import DebugToolbarExtension
from sqlalchemy.exc import IntegrityError
from flask_jwt import JWT, jwt_required,jwt_encode_handler, current_identity
from flask_sqlalchemy import SQLAlchemy
from collections.abc import Mapping
from models import db, connect_db, User, Property, Booking
from user_blueprint import users
from auth_blueprint import auth

s3 = boto3.resource('s3')

load_dotenv()

CURR_USER_KEY = "curr_user"

app = Flask(__name__)
app.register_blueprint(users)
app.register_blueprint(auth)

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['DATABASE_URL']
app.config['SQLALCHEMY_ECHO'] = False
app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = False
app.config['SECRET_KEY'] = os.environ['SECRET_KEY']
# toolbar = DebugToolbarExtension(app)

db = SQLAlchemy(app)

connect_db(app)

### login decorator ###

def authenticate(username, password):
    user = db.query.get_or_404(username)
    if user and password == user.password:
        return user

def identity(payload):
    user_id = payload['identity']
    return User.get_by_id(user_id)

jwt = JWT(app, authenticate, identity)



