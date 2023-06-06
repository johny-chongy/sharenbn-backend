from flask import Blueprint, jsonify

users = Blueprint('users', __name__)

@users.get("/<username>")
def get_user_info(username):
    """Returns JSON of user data:
    {first_name, last_name, email, is_owner}

    """