import os
import boto3
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from datetime import datetime
from sqlalchemy.exc import IntegrityError
from models import db, connect_db, User, Property, Booking
from aws_s3 import Aws, AWS_ACCESS_KEY, AWS_SECRET_ACCESS_KEY
from flask_cors import CORS, cross_origin
from flask_jwt_extended import (
    create_access_token,
    get_jwt_identity,
    jwt_required,
    JWTManager,
)

s3 = boto3.resource("s3")

load_dotenv()

app = Flask(__name__)
CORS(app)

app.config["SQLALCHEMY_ECHO"] = True
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["DEBUG_TB_INTERCEPT_REDIRECTS"] = False
app.config["SECRET_KEY"] = os.environ["SECRET_KEY"]
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ["DATABASE_URL"]
app.config["CORS_HEADERS"] = "Content-Type"

# Initialize AWS S3 client
s3 = boto3.client(
    "s3",
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY
)

connect_db(app)
jwt = JWTManager(app)
TIME_FORMAT = "%Y-%m-%d"


############################# AUTH ############################


@app.post("/auth/signup")
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
        access_token = create_access_token(identity=user.username,
                                           expires_delta=False)
        return jsonify(access_token=access_token)

    return jsonify({"error": "Invalid credentials"}), 401


@app.post("/auth/login")
def login_user():
    """Handle user login.
    Return JSON of JWT.
    If Login with invalid credentials, return JSON: invalid.
    """
    username = request.form.get("username")
    password = request.form.get("password")

    user = User.authenticate(username, password)

    if user:
        access_token = create_access_token(identity=user.username,
                                           expires_delta=False)
        return jsonify(access_token=access_token)

    return jsonify({"error": "Invalid credentials"}), 401


############################# USER ############################


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
    current_user = get_jwt_identity()

    if current_user != username:
        return jsonify({"error": "Invalid Authorization"})

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

    current_user = get_jwt_identity()

    if current_user != username:
        return jsonify({"error": "Invalid Authorization"})

    user = User.query.get_or_404(username)

    db.session.delete(user)
    db.session.commit()

    return jsonify(deleted=user.username)


################## PROPERTY ######################


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
        return jsonify({"error": error})


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

    current_user = get_jwt_identity()

    if current_user != property.owner.username:
        return jsonify(error="Invalid Authorization")

    property.address = request.form.get("address", property.address)
    property.sqft = request.form.get("sqft", property.sqft)
    property.price_rate = request.form.get("price_rate", property.price_rate)
    property.description = request.form.get(
        "description", property.description)

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
        return jsonify({"error": f"Duplicate address: {property.address}"})


@app.delete("/property/<int:property_id>")
@jwt_required()
def delete_property(property_id):
    """handles DELETE request to delete specific property based on id

    Return JSON for confirmation message
    """

    property = Property.query.get_or_404(property_id)

    current_user = get_jwt_identity()

    if current_user != property.owner.username:
        return jsonify({"error": "Invalid Authorization"})

    db.session.delete(property)
    db.session.commit()

    return jsonify(deleted=property.address)


############### BOOKING ################


@app.post("/property/<int:property_id>/bookings")
@jwt_required()
def book_property(property_id):
    """Given property Id
    Create a booking in the DB
    return JSON with booking info
    """

    property = Property.query.get_or_404(property_id)
    start_date_str = request.form.get("start_date")
    end_date_str = request.form.get("end_date")

    start_date = datetime.strptime(start_date_str, TIME_FORMAT)
    end_date = datetime.strptime(end_date_str, TIME_FORMAT)
    total_price = (end_date - start_date).days * property.price_rate
    current_user = get_jwt_identity()

    if current_user == property.owner.username:
        return jsonify({"error": "Owner cannot book own property"})

    try:
        Booking.verify_dates(start_date=start_date,
                             end_date=end_date,
                             property_id=property.id)

        booking = Booking.add_booking(
            address=property.address,
            username=current_user,
            total_price=total_price,
            start_date=start_date,
            end_date=end_date,
        )

        return jsonify(booking=booking.serialize())
    except ValueError:
        return jsonify({"error":'Start date is after end date.'}), 500
        # return jsonify(error="start date is after end date")
    except MemoryError:
        return jsonify({"error":'Dates are already booked.'}), 500
        # return jsonify(error="dates are already booked")


@app.get("/property/<int:property_id>/bookings")
@jwt_required()
def get_property_bookings(property_id):
    """Given a property id
    Return JSON of all the property bookings
    """
    property = Property.query.get_or_404(property_id)

    if get_jwt_identity() != property.owner.username:
        return jsonify({"error": "Invalid Authorization"})

    return jsonify(bookings=[b.serialize() for b in property.bookings])


@app.get("/user/<username>/bookings")
@jwt_required()
def get_user_bookings(username):
    """Given a username
    Return JSON of all the bookings for that user
    """
    user = User.query.get_or_404(username)

    if get_jwt_identity() != username:
        return jsonify({"error": "Invalid Authorization"})

    return jsonify(bookings=[b.serialize() for b in user.bookings])


@app.get("/bookings/<int:booking_id>")
@jwt_required()
def get_booking(booking_id):
    """Given a booking id
    Return JSON of the booking
    """
    current_user = get_jwt_identity()
    booking = Booking.query.get_or_404(booking_id)
    property = Property.query.filter_by(address=booking.address).first()

    if (current_user != booking.username) and (property.owner.username != current_user):
        return jsonify({"error": "Invalid Authorization"})

    return jsonify(booking=booking.serialize())


@app.patch("/bookings/<int:booking_id>")
@jwt_required()
def update_booking(booking_id):
    """Given a property id
    Update the booking in the database
    Return JSON of all the updated property booking
    """
    booking = Booking.query.get_or_404(booking_id)
    property = Property.query.filter_by(address=booking.address).first()

    start_date_str = request.form.get("start_date",
                                      datetime.strftime(booking.start_date,
                                                        TIME_FORMAT))
    end_date_str = request.form.get("end_date",
                                    datetime.strftime(booking.end_date,
                                                      TIME_FORMAT))

    booking.start_date = datetime.strptime(start_date_str, TIME_FORMAT)
    booking.end_date = datetime.strptime(end_date_str, TIME_FORMAT)
    booking.total_price = (
        booking.end_date - booking.start_date).days * property.price_rate
    current_user = get_jwt_identity()

    if current_user != booking.customer.username:
        return jsonify({"error": "Invalid Authorization"})

    try:
        Booking.verify_dates(start_date=booking.start_date,
                             end_date=booking.end_date,
                             property_id=property.id,
                             booking_id=booking_id)

        db.session.commit()
        return jsonify(booking=booking.serialize())
    except ValueError:
        return jsonify({"error":'Start date is after end date.'}), 500
        # return jsonify(error="start date is after end date")
    except MemoryError:
        return jsonify({"error":'Dates are already booked.'}), 500
        # return jsonify(error="dates are already booked")


@app.delete("/bookings/<int:booking_id>")
@jwt_required()
def delete_booking(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    current_user = get_jwt_identity()

    if current_user != booking.customer.username:
        return jsonify(error="Invalid authorization")

    db.session.delete(booking)
    db.session.commit()

    return jsonify(deleted=f"Booking at {booking.address} deleted")
