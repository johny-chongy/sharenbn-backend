"""SQLAlchemy models for Warbler."""

from datetime import datetime

from flask_bcrypt import Bcrypt
from flask_sqlalchemy import SQLAlchemy

bcrypt = Bcrypt()
db = SQLAlchemy()



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
    def signup(cls, username, email, password, image_url=DEFAULT_IMAGE_URL):
        """Sign up user.

        Hashes password and adds user to session.
        """

        hashed_pwd = bcrypt.generate_password_hash(password).decode('UTF-8')

        user = User(
            username=username,
            email=email,
            password=hashed_pwd,
            image_url=image_url,
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

    customers = db.relationship(
        'User',
        secondary='bookings',
        backref='booked_properties',
    )

    bookings = db.relationship('Booking', backref='property')

    def __repr__(self):
        return f"<User #{self.id}: {self.username}, {self.email}>"


    def is_followed_by(self, other_user):
        """Is this user followed by `other_user`?"""

        found_user_list = [
            user for user in self.followers if user == other_user]
        return len(found_user_list) == 1

    def is_following(self, other_user):
        """Is this user following `other_use`?"""

        found_user_list = [
            user for user in self.following if user == other_user]
        return len(found_user_list) == 1


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


class Amenity(db.Model):
    """Amenities for a property"""

    __tablename__ = 'amenities'

    feature = db.Column(
        db.String(30),
        primary_key=True,
    )


class Property_Amenity(db.Model):
    """Amenities mapped to a property"""

    __tablename__ = 'properties_amenities'

    feature = db.Column(
        db.String(30),
        db.ForeignKey('Amenity.feature', ondelete='CASCADE')
    )

    address = db.Column(
        db.String,
        db.ForeignKey('Property.address', ondelete='CASCADE')
    )

    __table_args__ = (db.PrimaryKeyConstraint(feature, address))


def connect_db(app):
    """Connect this database to provided Flask app.

    You should call this in your Flask app.
    """

    app.app_context().push()
    db.app = app
    db.init_app(app)
