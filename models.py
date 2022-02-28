from datetime import datetime

from flask import Flask
from flask_login import LoginManager, UserMixin
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
db = SQLAlchemy()


class OrderSummary(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    seller_id = db.Column(db.String(8))
    unique_id = db.Column(db.String(8))
    payment_method = db.Column(db.String(15))
    order_time = db.Column(db.DateTime, default=datetime.now())
    items = db.Column(db.String(256))
    total_cost = db.Column(db.Integer)
    quantity = db.Column(db.Integer)
    address = db.Column(db.Text())
    order_done = db.Column(db.Boolean(), default=False)


class Cart(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    unique_id = db.Column(db.String(8), unique=True)
    seller_id = db.Column(db.String(8))
    total_cost = db.Column(db.Integer)
    quantity = db.Column(db.Integer)
    items = db.Column(db.String(256))


class Menu(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    unique_id = db.Column(db.String(8))
    item_id = db.Column(db.Integer, unique=True)
    name = db.Column(db.String(256))
    price = db.Column(db.Integer)
    image_name = db.Column(db.String(256))
    category = db.Column(db.String(256))
    quantity = db.Column(db.String(256))


class Register(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    unique_id = db.Column(db.String(8), unique=True)
    first_name = db.Column(db.String(256))
    last_name = db.Column(db.String(256))
    email = db.Column(db.String(256), unique=True)
    mobile_num = db.Column(db.String(20), unique=True)
    date = db.Column(db.DateTime, default=datetime.now())


class Users(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    unique_id = db.Column(db.String(8), unique=True)
    user_name = db.Column(db.String(256), unique=True)
    email = db.Column(db.String(256), unique=True)
    password = db.Column(db.String(256))
    is_farmer = db.Column(db.Boolean(), default=False)

    def __init__(self, unique_id, user_name, email,
                 password, is_farmer):
        self.unique_id = unique_id
        self.user_name = user_name
        self.email = email
        self.is_farmer = is_farmer
        if password is not None:
            self.password = generate_password_hash(password)
        else:
            self.password = password

    def check_password(self, password):
        return check_password_hash(self.password, password)


login_manager = LoginManager()
login_manager.login_view = 'signup'


@login_manager.user_loader
def load_user(user_id):
    return Users.query.get(int(user_id))
