import os
import boto3
import botocore
from dotenv import load_dotenv
import json

from flask import Flask, request, session, g, jsonify

from flask_debugtoolbar import DebugToolbarExtension
from sqlalchemy.exc import IntegrityError, PendingRollbackError

# from flask_jwt import JWT, jwt_required, current_identity
from flask_jwt_extended import (
    create_access_token,
    get_jwt_identity,
    jwt_required,
    JWTManager,
)
from flask_sqlalchemy import SQLAlchemy
from models import db, connect_db, User, Property, Booking
from aws_s3 import Aws, AWS_ACCESS_KEY, AWS_BUCKET_NAME, AWS_SECRET_ACCESS_KEY

# from user_blueprint import users
# from auth_blueprint import auth

s3 = boto3.resource("s3")

load_dotenv()

CURR_USER_KEY = "curr_user"

app = Flask(__name__)
# app.register_blueprint(users)
# app.register_blueprint(auth)

app.config["SQLALCHEMY_ECHO"] = True
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["DEBUG_TB_INTERCEPT_REDIRECTS"] = False
app.config["SECRET_KEY"] = os.environ["SECRET_KEY"]
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ["DATABASE_URL"]


# toolbar = DebugToolbarExtension(app)

# Initialize AWS S3 client
s3 = boto3.client(
    "s3", aws_access_key_id=AWS_ACCESS_KEY, aws_secret_access_key=AWS_SECRET_ACCESS_KEY
)

connect_db(app)


def authenticate(username, password):
    user = db.query.get_or_404(username)
    if user and password == user.password:
        return user


def identity(payload):
    user_id = payload["identity"]
    return User.get_by_id(user_id)


# jwt = JWT(app, authenticate, identity)
jwt = JWTManager(app)

############################# USERS ############################
@app.post("/user")
# @expects_json(user_registration_schema)
def register_user():
    """Handle user signup.

    Create new user and add to DB. Return JWT

    If the there already is a user with that username: return JSON error
    """

    username = request.form.get("username")
    password = request.form.get("password")
    first_name = request.form.get("first_name")
    last_name = request.form.get("last_name")
    email = request.form.get("email")

    user = User.signup(
        username=username,
        password=password,
        first_name=first_name,
        last_name=last_name,
        email=email,
    )
    if user:
        # Generate the JWT token with the username payload
        access_token = create_access_token(identity=user.username, expires_delta=False)
        return jsonify(access_token=access_token)

    return jsonify({"message": "Invalid credentials"}), 401


@app.get("/user/<username>")
@jwt_required()
def show_user(username):
    """Given a username
    Return JSON with user info
    """

    user = User.query.get_or_404(username)
    return jsonify(user=user.serialize())


@app.patch("/user/<username>")
@jwt_required()
def update_user(username):
    """Given a username and formData
    Return JSON with updated user info
    """
    jwt_user = get_jwt_identity()

    if jwt_user != username:
        return jsonify(error="Invalid Authorization")

    user = User.query.get_or_404(username)

    user.first_name = request.form.get("first_name", user.first_name)
    user.last_name = request.form.get("last_name", user.last_name)
    user.email = request.form.get("email", user.email)

    db.session.commit()

    return jsonify(user=user.serialize())


@app.delete("/user/<username>")
@jwt_required()
def delete_user(username):
    """Given a username
    Delete user from db
    Return JSON with delete confirmation
    """

    jwt_user = get_jwt_identity()

    if jwt_user != username:
        return jsonify(error="Invalid Authorization")

    user = User.query.get_or_404(username)

    db.session.delete(user)
    db.session.commit()

    return jsonify(deleted=user.username)


################## PROPERTY ROUTES ######################


@app.post("/property")
@jwt_required()
def add_property():
    """Handles POST request for new property registration.

    Create new property and add to DB & upload files to S3

    Return JSON for newly created property
    """

    address = request.form.get("address")
    sqft = request.form.get("sqft")
    description = request.form.get("description")
    owner = User.query.get_or_404(get_jwt_identity())
    price_rate = request.form.get("price_rate")

    img_file = request.files["file"]
    img_file_name = Aws.upload_file(img_file)
    img_url = Aws.get_file_url(img_file_name)

    try:
        property = Property.add_property(
            address, price_rate, owner, sqft, img_url, description
        )
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
@jwt_required()
def edit_property(property_id):
    """handles PATCH request to edit specific property based on id

    Return JSON for newly updated property
    """

    property = Property.query.get_or_404(property_id)

    jwt_user = get_jwt_identity()

    if jwt_user != property.owner.username:
        return jsonify(error="Invalid Authorization")

    property.address = request.form.get("address", property.address)
    property.sqft = request.form.get("sqft", property.sqft)
    property.price_rate = request.form.get("price_rate", property.price_rate)
    property.description = request.form.get("description", property.description)

    img_file = request.files.get("file")

    if img_file:
        img_file_name = Aws.upload_file(img_file)
        property.img_url = Aws.get_file_url(img_file_name)

    try:
        db.session.commit()
        serialized_updated_property = property.serialize()
        return jsonify(property=serialized_updated_property)
    except IntegrityError:
        db.session.rollback()
        return jsonify(error=f"Duplicate address: {property.address}")


@app.delete("/property/<int:property_id>")
@jwt_required()
def delete_property(property_id):
    """handles DELETE request to delete specific property based on id

    Return JSON for confirmation message
    """

    property = Property.query.get_or_404(property_id)

    jwt_user = get_jwt_identity()

    if jwt_user != property.owner.username:
        return jsonify(error="Invalid Authorization")

    db.session.delete(property)
    db.session.commit()

    return jsonify(deleted=property.address)


############### Bookings Routes ################
@app.post("/property/<int:property_id>/bookings")
@jwt_required()
def book_property(property_id):
    """Given property Id
    Create a booking in the DB
    return JSON with booking info
    """
    start_date = request.form.get('start_date')
    end_date = request.form.get('end_date')
    total_days =

    property = Property.query.get_or_404(property_id)
    booking = Booking.add_booking(
        address=property.address,
        )
    return jsonify(booking=booking)

@app.get("/property/<int:property_id>/bookings")
def get_property_bookings(property_id):
    """Given a property id
    Return JSON of all the property bookings
    """
    property = Property.query.get_or_404(property_id)
    return jsonify(bookings=[b.serialize() for b in property.bookings])
