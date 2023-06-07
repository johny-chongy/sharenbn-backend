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

app.config['SQLALCHEMY_ECHO'] = False
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

## PROPERTY ##
@app.post("/property")
def add_property():
    """Handle new property registration.

    Create new property and add to DB & upload files to S3

    Return success confirmation message
    """

    json_data = request.form.get('json_data')
    parsed_json_data = json.loads(json_data)
    img_file = request.files['file']
    img_file_name = Aws.upload_file(img_file)

    img_url = Aws.get_file_url(img_file_name)
    address = parsed_json_data['address']
    sqft = parsed_json_data['sqft']
    # amenities = parsed_json_data['amenities']
    # description = parsed_json_data['description']
    owner = parsed_json_data['owner']
    price_rate = parsed_json_data['price_rate']
    # breakpoint()
    # new_property = Property(
    #     address=address,
    #     sqft=sqft,
    #     owner=owner,
    #     price_rate=price_rate,
    #     img_url=img_url
    # )

    # db.session.add(new_property)
    Property.add_property(
        address=address,
        sqft=sqft,
        owner=owner,
        price_rate=price_rate
    )

    db.session.commit()


    return "property upload successful"


@app.get("/property")
def get_property():
    try:

        file_name=request.json['img_name']
        # Generate a pre-signed URL for the file
        url = s3.generate_presigned_url('get_object',
                                        Params={'Bucket': AWS_BUCKET_NAME,
                                                'Key': file_name},
                                        ExpiresIn=3600)  # URL expiration time in seconds

        # Return the URL as a JSON response
        return jsonify({'url': url})
    except botocore.exceptions.NoCredentialsError:
        return 'Error: AWS credentials not found.', 500
    except botocore.exceptions.ParamValidationError:
        return 'Error: Invalid bucket or file name.', 400
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchKey':
            return 'Error: File not found.', 404
        else:
            return 'Error: Failed to retrieve file URL.', 500




