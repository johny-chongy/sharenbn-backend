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

    properties = db.relationship(
        'Property',
        backref='owner',
        cascade='all, delete-orphan'
    )

    bookings = db.relationship(
        'Booking',
        backref='customer',
        cascade='all, delete-orphan'
    )

    def serialize(self):
        """Serialize to dictionary."""

        return {
            "username": self.username,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "email": self.email,
            "properties": [p.serialize() for p in self.properties],
            "bookings": [b.serialize() for b in self.bookings]
        }

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
            last_name=last_name
        )

        db.session.add(user)
        db.session.commit()
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

    id = db.Column(
        db.Integer,
        primary_key=True,
        autoincrement=True
    )

    address = db.Column(
        db.String,
        unique=True
    )

    price_rate = db.Column(
        db.Integer,
        nullable=False,
    )

    user = db.Column(
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

    description =db.Column(
        db.String,
        default=""
    )

    customers = db.relationship(
        'User',
        secondary='bookings',
        backref='booked_properties',
    )

    bookings = db.relationship(
        'Booking',
        backref='property',
        cascade='all, delete-orphan'
    )


    def serialize(self):
        """Serialize to dictionary."""

        return {
            "id":self.id,
            "address": self.address,
            "price_rate": self.price_rate,
            "owner": self.user,
            "sqft": self.sqft,
            "img_url": self.img_url,
            "description":self.description
        }

    @classmethod
    def add_property(cls, address, price_rate, owner, sqft, img_url,description):
        """Creates property listing.

        Adds property to database
        """

        location = Property(
            address=address,
            price_rate=price_rate,
            owner=owner,
            sqft=sqft,
            img_url=img_url,
            description=description
        )

        db.session.add(location)
        db.session.commit()
        return location



class Booking(db.Model):
    """An individual booking."""

    __tablename__ = 'bookings'

    id = db.Column(
        db.Integer,
        primary_key=True,
        autoincrement=True
    )

    address = db.Column(
        db.String,
        db.ForeignKey('properties.address', ondelete='CASCADE')
    )

    username = db.Column(
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

    # review = db.Column(
    #     db.String
    # )

    # rating = db.Column(
    #     db.Integer
    # )

    def serialize(self):
        """Serialize to dictionary."""

        return {
            "id":self.id,
            "address":self.address,
            "customer": self.username,
            "total_price": self.total_price,
            "start_date": self.start_date,
            "end_date": self.end_date,
        }


    @classmethod
    def verify_dates(cls, start_date, end_date, property_id, booking_id=None):
        """Verifies:
                -start_date < end_date
                -dates do not coincide with any other booking dates
        """
        if (start_date > end_date):
            raise ValueError()

        property_bookings = Property.query.get_or_404(property_id).bookings
        filtered_bookings = [b_filter for b_filter in property_bookings
                             if b_filter.id != booking_id]

        dates_validated = all(
                ((start_date < b.start_date and end_date < b.start_date)
            or (start_date > b.end_date and end_date > b.end_date))
                for b in filtered_bookings
                )

        if (not dates_validated):
            raise MemoryError()

        return dates_validated

    @classmethod
    def add_booking(cls, address, username, total_price, start_date, end_date):
        """Creates property listing.

        Adds property to database
        """
        booking = Booking(
            address=address,
            username=username,
            total_price=total_price,
            start_date=start_date,
            end_date=end_date
        )

        db.session.add(booking)
        db.session.commit()
        return booking



