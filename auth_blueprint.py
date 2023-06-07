from flask import Flask, Blueprint, jsonify, g
from flask_expects_json import expects_json
from schemas import user_registration_schema
from flask_jwt import JWT, jwt_required,jwt_encode_handler, current_identity
from models import db, connect_db, User, Message, Like

auth = Blueprint('auth', __name__)



@auth.post("/")
@expects_json(user_registration_schema)
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



