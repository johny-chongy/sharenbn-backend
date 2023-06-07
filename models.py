"""SQLAlchemy models for Warbler."""

from datetime import datetime

from flask_bcrypt import Bcrypt
from flask_sqlalchemy import SQLAlchemy

bcrypt = Bcrypt()
db = SQLAlchemy()


def connect_db(app):
    """Connect this database to provided Flask app.

    You should call this in your Flask app.
    """

    app.app_context().push()
    db.app = app
    db.init_app(app)


class User(db.Model):
    """User for SharenBn"""

    __tablename__ = 'users'

    username = db.Column(
        db.String(30),
        primary_key=True
    )

    password = db.Column(
        db.String(100),
        nullable=False,
    )

    first_name = db.Column(
        db.String(20),
        nullable=False
    )

    last_name = db.Column(
        db.String(20),
        nullable=False
    )

    email = db.Column(
        db.String(50),
        nullable=False,
        unique=True,
    )

    owner = db.Column(
        db.Boolean,
        default=False
    )

    properties = db.relationship('Property', backref='owner')
    bookings = db.relationship('Booking', backref='customer')

    @classmethod
    def signup(cls, username, email, password, first_name, last_name):
        """Sign up user.

        Hashes password and adds user to session.
        """

        hashed_pwd = bcrypt.generate_password_hash(password).decode('UTF-8')

        user = User(
            username=username,
            email=email,
            password=hashed_pwd,
            first_name=first_name,
            last_name=last_name,
            owner=False
        )

        db.session.add(user)
        return user

    @classmethod
    def authenticate(cls, username, password):
        """Find user with `username` and `password`.

        This is a class method (call it on the class, not an individual user.)
        It searches for a user whose password hash matches this password
        and, if it finds such a user, returns that user object.

        If this can't find matching user (or if password is wrong), returns
        False.
        """

        user = cls.query.filter_by(username=username).one_or_none()

        if user:
            is_auth = bcrypt.check_password_hash(user.password, password)
            if is_auth:
                return user

        return False



class Property(db.Model):
    """Property in the system."""

    __tablename__ = 'properties'

    address = db.Column(
        db.String,
        primary_key=True,
    )

    price_rate = db.Column(
        db.Integer,
        nullable=False,
    )

    owner = db.Column(
        db.String(30),
        db.ForeignKey('users.username', ondelete='CASCADE')
    )

    sqft = db.Column(
        db.Integer,
        nullable=False
    )

    img_url = db.Column(
        db.String,
        nullable=False
    )

    customers = db.relationship(
        'User',
        secondary='bookings',
        backref='booked_properties',
    )

    bookings = db.relationship('Booking', backref='property')

    @classmethod
    def add_property(cls, address, price_rate, owner, sqft):
        """Creates property listing.

        Adds property to database
        """

        location = Property(
            address=address,
            price_rate=price_rate,
            owner=owner,
            sqft=sqft
        )

        db.session.add(location)
        return location


class Booking(db.Model):
    """An individual booking."""

    __tablename__ = 'bookings'

    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    address = db.Column(
        db.String,
        db.ForeignKey('properties.address', ondelete='CASCADE')
    )

    customer = db.Column(
        db.String(30),
        db.ForeignKey('users.username', ondelete='CASCADE')
    )

    total_price = db.Column(
        db.Integer,
        nullable=False
    )

    start_date = db.Column(
        db.DateTime,
        nullable=False
    )

    end_date = db.Column(
        db.DateTime,
        nullable=False
    )

    review = db.Column(
        db.String
    )

    rating = db.Column(
        db.Integer
    )


