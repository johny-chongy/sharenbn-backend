import os
import boto3
import botocore
from dotenv import load_dotenv
import json

from flask import Flask, request, session, g, jsonify

from flask_debugtoolbar import DebugToolbarExtension
from sqlalchemy.exc import IntegrityError
# from flask_jwt import JWT, jwt_required,jwt_encode_handler, current_identity
from flask_sqlalchemy import SQLAlchemy
from models import db, connect_db, User, Property, Booking
from aws_s3 import Aws, AWS_ACCESS_KEY, AWS_BUCKET_NAME, AWS_SECRET_ACCESS_KEY
# from user_blueprint import users
# from auth_blueprint import auth

s3 = boto3.resource('s3')

load_dotenv()

CURR_USER_KEY = "curr_user"

app = Flask(__name__)
# app.register_blueprint(users)
# app.register_blueprint(auth)

app.config['SQLALCHEMY_ECHO'] = True
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = False
app.config['SECRET_KEY'] = os.environ['SECRET_KEY']
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['DATABASE_URL']


# toolbar = DebugToolbarExtension(app)

# Initialize AWS S3 client
s3 = boto3.client('s3',
                  aws_access_key_id=AWS_ACCESS_KEY,
                  aws_secret_access_key= AWS_SECRET_ACCESS_KEY)

connect_db(app)

### login decorator ###

def authenticate(username, password):
    user = db.query.get_or_404(username)
    if user and password == user.password:
        return user

def identity(payload):
    user_id = payload['identity']
    return User.get_by_id(user_id)

# jwt = JWT(app, authenticate, identity)

## USERS ##
@app.post("/user")
# @expects_json(user_registration_schema)
def register_user():
    """Handle user signup.

    Create new user and add to DB. Return JWT

    If the there already is a user with that username: return JSON error
    """

    username = g.data.get("username")
    password = g.data.get("password")
    first_name = g.data.get("first_name")
    last_name = g.data.get("last_name")
    email = g.data.get("email")

    user = User.signup(username=username, password=password, first_name=first_name, last_name=last_name, email=email)
    if user:
        # Generate the JWT token with the username payload
        payload = {'username': user.username}
        token = jwt_encode_handler(payload)
        return jsonify({'token': token.decode('utf-8')})

    return jsonify({'message': 'Invalid credentials'}), 401


## PROPERTY ROUTES ##
@app.post("/property")
def add_property():
    """Handles POST request for new property registration.

    Create new property and add to DB & upload files to S3

    Return JSON for newly created property
    """

    address = request.form.get('address')
    sqft = request.form.get('sqft')
    description = request.form.get('description')
    owner = User.query.get_or_404(request.form.get('owner'))
    price_rate = request.form.get('price_rate')

    img_file = request.files['file']
    img_file_name = Aws.upload_file(img_file)
    img_url = Aws.get_file_url(img_file_name)

    try:
        property = Property.add_property(address,
                                         price_rate,
                                         owner,
                                         sqft,
                                         img_url,
                                         description)
        return (jsonify(property=property.serialize()), 201)

    except IntegrityError:
        error = f"Property address ({address}) already listed"
        return jsonify(error=error)


@app.get("/property")
def get_all_properties():
    """handles GET request to read all properties

    Return JSON array for all properties
    """

    properties = Property.query.all()
    serialized_properties = [p.serialize() for p in properties]

    return (jsonify(properties=serialized_properties), 200)


@app.get("/property/<int:property_id>")
def get_property(property_id):
    """handles GET request to read specific property based on id

    Return JSON for searched property
    """

    property = Property.query.get_or_404(property_id)
    return (jsonify(property=property.serialize()), 200)


@app.patch("/property/<int:property_id>")
def edit_property(property_id):
    """handles PATCH request to edit specific property based on id

    Return JSON for newly updated property
    """

    property = Property.query.get_or_404(property_id)

    property.address = request.form.get('address', property.address)
    property.sqft = request.form.get('sqft', property.sqft)
    property.price_rate = request.form.get('price_rate', property.price_rate)
    property.description = request.form.get('description', property.description)

    img_file = request.files.get('file')

    if img_file:
        img_file_name = Aws.upload_file(img_file)
        property.img_url = Aws.get_file_url(img_file_name)

    db.session.commit()

    serialized_updated_property = property.serialize()

    return jsonify(property=serialized_updated_property)


@app.delete("/property/<int:property_id>")
def delete_property(property_id):
    """handles DELETE request to delete specific property based on id

    Return JSON for confirmation message
    """

    property = Property.query.get_or_404(property_id)

    db.session.delete(property)
    db.session.commit()

    return jsonify(deleted = property.address)





