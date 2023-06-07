from csv import DictReader
from app import db
from models import User, Property, Booking
from flask_bcrypt import Bcrypt

bcrypt = Bcrypt()

db.drop_all()
db.create_all()


hashed_test_pswd = bcrypt.generate_password_hash('password').decode('UTF-8')


test_user1 = User(
    username='testyzesty1',
    first_name='testy',
    last_name='zesty',
    email='testy@zesty.com',
    password=hashed_test_pswd
)

db.session.add(test_user1)
db.session.commit()