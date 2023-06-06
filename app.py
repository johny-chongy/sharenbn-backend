import os
import functools
from dotenv import load_dotenv

from flask import Flask, render_template, request, flash, redirect, session, g
from flask_debugtoolbar import DebugToolbarExtension
from sqlalchemy.exc import IntegrityError

from forms import UserAddForm, UserEditForm, LoginForm, MessageForm, CSRFProtectForm
from models import db, connect_db, User, Message, Like

from user_blueprint import users
from auth_blueprint import auth

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

connect_db(app)

### login decorator ###


