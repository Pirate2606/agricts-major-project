import json
import os
import re
import string
import uuid

from flask import render_template, request, redirect, url_for, g, session, abort, flash
from flask_login import login_user, logout_user, login_required, current_user
from flask_migrate import Migrate
from wtforms import ValidationError

from cli import create_db
from config import Config
from models import app, db, Register, login_manager, Users, Menu, Cart, OrderSummary
from sendMail import send_mail, send_order_mail

# flask migration connecting the app and the database
Migrate(app, db)

# configuring the app
app.config.from_object(Config)
app.cli.add_command(create_db)
db.init_app(app)
login_manager.init_app(app)



@app.route('/')
def home():
    if not session.get('user_id'):
        return render_template("home.html")
    else:
        unique_id = Users.query.filter_by(
            id=session['user_id']).first().unique_id
        is_farmer = Users.query.filter_by(
            unique_id=unique_id).first().is_farmer
        if Register.query.filter_by(unique_id=unique_id).first() is None:
            return redirect(url_for("registration_form", unique_id=unique_id))
        return render_template("home.html", unique_id=unique_id, is_farmer=is_farmer)


@app.route('/<unique_id>/admin', methods=['GET', 'POST'])
@login_required
def admin_panel(unique_id):
    is_order = request.args.get('o')
    remove = request.args.get('r')
    order_done = request.args.get('d')
    if not session.get('user_id'):
        return redirect(url_for('signup'))
    elif Users.query.filter_by(id=session.get('user_id')).first().unique_id != unique_id:
        abort(403)
    elif not Users.query.filter_by(unique_id=unique_id).first().is_farmer:
        abort(403)
    if Register.query.filter_by(unique_id=unique_id).first() is None:
        return redirect(url_for("registration_form", unique_id=unique_id))
    if order_done:
        order_ = OrderSummary.query.filter_by(id=int(order_done)).first()
        order_.order_done = True
        db.session.add(order_)
        db.session.commit()
        return redirect(url_for('admin_panel', unique_id=unique_id, o=1))
    if request.method == "POST":
        name = request.form['product']
        price = request.form['price']
        url = request.form['url']
        category = request.form['category']
        quantity = request.form['quantity']
        total = len(Menu.query.all())
        menu = Menu(
            unique_id=unique_id,
            item_id=total+1,
            name=name,
            price=price,
            image_name=url,
            category=category,
            quantity=quantity,
        )
        db.session.add(menu)
        db.session.commit()
        return redirect(url_for('admin_panel', unique_id=unique_id))
    if remove:
        menu = Menu.query.filter_by(id=int(remove)).first()
        db.session.delete(menu)
        db.session.commit()
        return redirect(url_for('admin_panel', unique_id=unique_id))
    if is_order:
        names = []
        order_date = []
        order_time = []
        orders = OrderSummary.query.filter_by(seller_id=unique_id).all()
        for order in orders:
            user = Register.query.filter_by(unique_id=order.unique_id).first()
            names.append(user.first_name + " " + user.last_name)
            order_date.append(order.order_time.strftime("%d-%m-%Y"))
            order_time.append(order.order_time.strftime("%H:%M:%S"))
        return render_template('admin_orders.html', 
                               orders=orders, 
                               unique_id=unique_id, 
                               names=names, 
                               order_date=order_date, 
                               order_time=order_time)
    else:
        menu = Menu.query.filter_by(unique_id=unique_id).all()
        return render_template('admin.html', menu=menu, unique_id=unique_id)


@app.route('/<unique_id>/order_summary', methods=["POST", "GET"])
@login_required
def order_summary(unique_id):
    order = request.args.get("o")
    order_quantity = request.args.get("q")
    seller_id = request.args.get("s")
    if not session.get('user_id'):
        return redirect(url_for('signup'))
    elif Users.query.filter_by(id=session.get('user_id')).first().unique_id != unique_id:
        abort(403)
    if Register.query.filter_by(unique_id=unique_id).first() is None:
        return redirect(url_for("registration_form", unique_id=unique_id))
    user_cart = Cart.query.filter_by(unique_id=unique_id).first()
    is_farmer = Users.query.filter_by(unique_id=unique_id).first().is_farmer
    if user_cart is None and not order:
        return redirect(url_for("cart", unique_id=unique_id))
    user = Register.query.filter_by(unique_id=unique_id).first()
    summary = OrderSummary.query.filter_by(unique_id=unique_id).all()
    latest = None
    for s in summary:
        latest = s
    user_name = user.first_name + " " + user.last_name
    phone_num = user.mobile_num
    date_time = latest.order_time
    order_date = date_time.strftime("%d/%m/%Y")
    order_time = date_time.strftime("%H:%M:%S")
    method = latest.payment_method
    name = []
    price = []
    quantity = []
    sellers = []
    seller_phone = []
    if not order:
        if request.method == "POST":
            all_items_ = json.loads(user_cart.items)
            for item in all_items_:
                mail_menu = Menu.query.filter_by(item_id=int(item)).first()
                email = Register.query.filter_by(
                    unique_id=mail_menu.unique_id).first().email
                send_order_mail(email)
            db.session.delete(user_cart)
            db.session.commit()
            return redirect(url_for("market", category="fruits"))
        total_cost = user_cart.total_cost
        all_items = json.loads(user_cart.items)
        total_items = len(all_items)
        for item in all_items:
            menu_ = Menu.query.filter_by(item_id=int(item)).first()
            name.append(menu_.name)
            price.append(menu_.price)
            quantity.append(all_items[item])
            sellers.append(Users.query.filter_by(
                unique_id=menu_.unique_id).first().user_name)
            seller_phone.append(Register.query.filter_by(
                unique_id=menu_.unique_id).first().mobile_num)
        latest.items = json.dumps(all_items)
        latest.total_cost = total_cost
        latest.quantity = sum(quantity)
    else:
        menu_ = Menu.query.filter_by(item_id=int(order)).first()
        if request.method == "POST":
            email = Register.query.filter_by(unique_id=menu_.unique_id).first().email
            send_order_mail(email)
            return redirect(url_for("market", category="fruits"))
        name.append(menu_.name)
        price.append(menu_.price)
        sellers.append(seller_id)
        seller_phone.append(Register.query.filter_by(
            unique_id=seller_id).first().mobile_num)
        quantity.append(order_quantity)
        total_cost = price[0] * int(order_quantity)
        total_items = 1
        latest.items = '{"' + str(order) + '" : ' + order_quantity + '}'
        latest.total_cost = total_cost
        latest.quantity = order_quantity
    db.session.add(latest)
    db.session.commit()
    return render_template("order-summary.html",
                           total_cost=total_cost,
                           name=name,
                           price=price,
                           quantity=quantity,
                           total_items=total_items,
                           phone_num=phone_num,
                           user_name=user_name,
                           order_date=order_date,
                           order_time=order_time,
                           method=method,
                           unique_id=unique_id,
                           is_farmer=is_farmer,
                           sellers=sellers,
                           seller_phone=seller_phone)


@app.route('/<unique_id>/payment', methods=["GET", "POST"])
@login_required
def payment(unique_id):
    order = request.args.get("o")
    quantity = request.args.get("q")
    seller_id = request.args.get("s")
    if not session.get('user_id'):
        return redirect(url_for('signup'))
    elif Users.query.filter_by(id=session.get('user_id')).first().unique_id != unique_id:
        abort(403)
    if Register.query.filter_by(unique_id=unique_id).first() is None:
        return redirect(url_for("registration_form", unique_id=unique_id))
    user_cart = Cart.query.filter_by(unique_id=unique_id).first()
    is_farmer = Users.query.filter_by(unique_id=unique_id).first().is_farmer
    if order is not None:
        menu_ = Menu.query.filter_by(item_id=int(order)).first()
        if request.method == "POST":
            method = request.form['paymentMethod']
            address = request.form["address"]
            if method == "1":
                method = "Credit Card"
            elif method == "2":
                method = "Debit Card"
            else:
                method = "Cash"
            summary = OrderSummary(
                unique_id=unique_id, seller_id=seller_id, payment_method=method, address=address)
            menu_.quantity = str(int(menu_.quantity) - int(quantity))
            db.session.add_all([summary, menu_])
            db.session.commit()
            return redirect(url_for('order_summary', unique_id=unique_id, o=order, q=quantity, s=seller_id))
    elif user_cart is None:
        return redirect(url_for('cart', unique_id=unique_id))
    elif (user_cart is not None) and (order is None):
        total_cost = user_cart.total_cost
        all_items = json.loads(user_cart.items)
        print(all_items)
        name = []
        price = []
        category = []
        quantity = []
        total_items = len(all_items)
        if request.method == "POST":
            method = request.form['paymentMethod']
            address = request.form["address"]
            if method == "1":
                method = "Credit Card"
            elif method == "2":
                method = "Debit Card"
            else:
                method = "Cash"
            summary = OrderSummary(unique_id=unique_id, payment_method=method,
                                   seller_id=user_cart.seller_id, address=address)
            db.session.add(summary)
            db.session.commit()
            return redirect(url_for('order_summary', unique_id=unique_id))
        for item in all_items:
            menu_ = Menu.query.filter_by(item_id=int(item)).first()
            menu_.quantity = str(int(menu_.quantity) - int(all_items[item]))
            name.append(menu_.name)
            price.append(menu_.price)
            cat = menu_.category
            cat = cat[0].upper() + cat[1:]
            category.append(cat)
            quantity.append(all_items[item])
            db.session.add(menu_)
            db.session.commit()

        return render_template("payment.html",
                               total_cost=total_cost,
                               price=price,
                               category=category,
                               name=name,
                               total_items=total_items,
                               unique_id=unique_id,
                               quantity=quantity,
                               is_farmer=is_farmer)

    return render_template('payment.html',
                           total_items=1,
                           total_cost=menu_.price * int(quantity),
                           name=[menu_.name],
                           price=[menu_.price],
                           category=[menu_.category],
                           unique_id=unique_id,
                           quantity=[int(quantity)],
                           is_farmer=is_farmer)


@app.route('/<item_id>/<unique_id>/remove_item')
def remove_item(item_id, unique_id):
    cart_ = Cart.query.filter_by(unique_id=unique_id).first()
    user_id = cart_.id
    items = json.loads(cart_.items)
    for item in items:
        if int(item) == int(item_id):
            menu_ = Menu.query.filter_by(item_id=int(item)).first()
            cart_.total_cost -= (menu_.price * items[item])
            cart_.quantity -= items[item]
            del items[item]
            break
    if len(items) == 0:
        del_cart = Cart.query.get(user_id)
        db.session.delete(del_cart)
        db.session.commit()
    else:
        cart_.items = json.dumps(items)
        db.session.add(cart_)
        db.session.commit()
    return {"success": True}


@app.route('/<unique_id>/cart')
@login_required
def cart(unique_id):
    if not session.get('user_id'):
        return redirect(url_for('signup'))
    elif Users.query.filter_by(id=session.get('user_id')).first().unique_id != unique_id:
        abort(403)
    if Register.query.filter_by(unique_id=unique_id).first() is None:
        return redirect(url_for("registration_form", unique_id=unique_id))
    user_cart = Cart.query.filter_by(unique_id=unique_id).first()
    is_farmer = Users.query.filter_by(unique_id=unique_id).first().is_farmer
    if user_cart is not None:
        total_cost = user_cart.total_cost
        all_items = json.loads(user_cart.items)
        name = []
        quantity = []
        price = []
        image = []
        category = []
        item_id = []
        total_items = len(all_items)
        for item in all_items:
            menu_ = Menu.query.filter_by(item_id=int(item)).first()
            item_id.append(int(item))
            name.append(menu_.name)
            quantity.append(all_items[item])
            price.append(menu_.price)
            image.append(menu_.image_name)
            cat = menu_.category
            cat = cat[0].upper() + cat[1:]
            category.append(cat)

        return render_template("cart.html",
                               total_cost=total_cost,
                               price=price,
                               image=image,
                               category=category,
                               quantity=quantity,
                               name=name,
                               total_items=total_items,
                               unique_id=unique_id,
                               item_id=item_id,
                               is_farmer=is_farmer)

    return render_template("cart.html", total_items=0, unique_id=unique_id, is_farmer=is_farmer)


@app.route('/market/<category>', methods=["GET", "POST"])
def market(category):
    food_menu = Menu()
    all_items = food_menu.query.filter_by(category=category).all()
    total_items = len(all_items)
    number_of_rows = (total_items // 3) + 1
    user_names = []

    for item in all_items:
        user_names.append(Users.query.filter_by(
            unique_id=item.unique_id).first().user_name)

    if request.method == "POST":
        if not session.get('user_id'):
            return redirect(url_for('signup'))
        else:
            unique_id = Users.query.filter_by(
                id=session['user_id']).first().unique_id
            is_farmer = Users.query.filter_by(
                unique_id=unique_id).first().is_farmer
            get_quantity = request.form['quantity'].split(" ")
            json_string = '{"' + \
                get_quantity[0] + '" : ' + get_quantity[1] + '}'
            item_id = int(get_quantity[0])
            quantity = int(get_quantity[1])
            if Cart.query.filter_by(unique_id=unique_id).first() is not None:
                cart_obj = Cart.query.filter_by(unique_id=unique_id).first()
                previous_json_quantity = cart_obj.items
                cart_obj.quantity += quantity
                cart_obj.total_cost += (quantity *
                                        Menu.query.filter_by(item_id=item_id).first().price)
                json_string = previous_json_quantity[:-1] + ', "' + \
                    get_quantity[0] + '" : ' + get_quantity[1] + '}'
                cart_obj.items = json_string
                db.session.add(cart_obj)
                db.session.commit()
            else:
                menu = Menu.query.filter_by(item_id=item_id).first()
                total_cost = quantity * menu.price
                cart_obj = Cart(unique_id=unique_id, total_cost=total_cost,
                                quantity=quantity, items=json_string, seller_id=menu.unique_id)
                db.session.add(cart_obj)
                db.session.commit()
    if not session.get('user_id'):
        cart_obj = None
        return render_template('menu.html',
                               all_items=all_items,
                               number_of_rows=number_of_rows,
                               total_items=total_items,
                               cart_obj=cart_obj,
                               category=category,
                               user_names=user_names)
    else:
        unique_id = Users.query.filter_by(
            id=session['user_id']).first().unique_id
        is_farmer = Users.query.filter_by(
            unique_id=unique_id).first().is_farmer
        if Register.query.filter_by(unique_id=unique_id).first() is None:
            return redirect(url_for("registration_form", unique_id=unique_id))
        item = Cart.query.filter_by(unique_id=unique_id).first()
        if item is not None:
            cart_obj = json.loads(item.items)
        else:
            cart_obj = None
        return render_template('menu.html',
                               all_items=all_items,
                               number_of_rows=number_of_rows,
                               total_items=total_items,
                               category=category,
                               cart_obj=cart_obj,
                               unique_id=Users.query.filter_by(
                                   id=session['user_id']).first().unique_id,
                               is_farmer=is_farmer,
                               user_names=user_names)


@app.route('/get_fruits')
def get_fruits():
    return {"success": True}


@app.route('/get_vegetables')
def get_vegetables():
    return {"success": True}


@app.route('/<unique_id>/profile')
@login_required
def profile(unique_id):
    if not session.get('user_id'):
        return redirect(url_for('signup'))
    elif Users.query.filter_by(id=session.get('user_id')).first().unique_id != unique_id:
        abort(403)
    if Register.query.filter_by(unique_id=unique_id).first() is None:
        return redirect(url_for("registration_form", unique_id=unique_id))
    register = Register.query.filter_by(unique_id=unique_id).first()
    registration_id = register.email.split("@")[0]
    registration_date = register.date.strftime("%d-%m-%Y")
    registration_time = register.date.strftime("%H:%M:%S")
    is_farmer = Users.query.filter_by(unique_id=unique_id).first().is_farmer
    orders = OrderSummary.query.filter_by(unique_id=unique_id).all()
    sellers = []
    order_date = []
    order_time = []
    items = []
    items_list = []
    if orders is not None:
        for order in orders:
            order_date.append(order.order_time.strftime("%d-%m-%Y"))
            order_time.append(order.order_time.strftime("%H:%M:%S"))
            items.append(json.loads(order.items))
            user = Register.query.filter_by(unique_id=order.seller_id).first()
            sellers.append(user.first_name + " " + user.last_name)
        for item in items:
            items_dict = {}
            for i in item:
                menu_ = Menu.query.filter_by(item_id=int(i)).first()
                items_dict[menu_.name] = item[i]
            items_list.append(items_dict)
    return render_template("profile.html",
                           register=register,
                           registration_id=registration_id,
                           unique_id=unique_id,
                           registration_time=registration_time,
                           registration_date=registration_date,
                           orders=orders,
                           order_time=order_time,
                           order_date=order_date,
                           items_list=items_list,
                           is_farmer=is_farmer,
                           sellers=sellers
                           )


@app.route('/<unique_id>/register', methods=['POST', 'GET'])
@login_required
def registration_form(unique_id):
    email = Users.query.filter_by(unique_id=unique_id).first().email
    if request.method == "POST":
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        email = request.form['email']
        mobile_num = request.form['mobile_num']
        if Register.query.filter_by(mobile_num=mobile_num).first() is not None:
            flash('This mobile number is already registered with some other account.')
            return redirect(url_for("registration_form", unique_id=unique_id))
        register = Register(unique_id=unique_id,
                            first_name=first_name,
                            last_name=last_name,
                            email=email,
                            mobile_num=mobile_num,
                            )
        db.session.add(register)
        db.session.commit()
        return redirect(url_for('profile', unique_id=unique_id))
    return render_template('registration-form.html', email=email)


@app.route("/check_login")
@login_required
def check_login():
    g.user = current_user.get_id()
    if g.user:
        user_id = int(g.user)
        user = Users.query.get(user_id)
        unique_id = user.unique_id
        has_registered = Register.query.filter_by(unique_id=unique_id).first()
        if has_registered is not None:
            return redirect(url_for('home'))
        return redirect(url_for('registration_form', unique_id=unique_id))


@app.route('/sign_up', methods=['GET', 'POST'])
def signup():
    if session.get("user_id"):
        return redirect(url_for('home'))
    email_flag = False
    username_flag = False
    password_flag = False

    if request.method == "POST":
        user_name = request.form['username']
        email = request.form['email']
        password = request.form['password']
        is_farmer = request.form['is_farmer']
        if is_farmer == "true":
            is_farmer = True
        else:
            is_farmer = False

        password_flag = check_password(password)
        try:
            email_flag = check_mail(email)
        except ValidationError:
            email_flag = True

        try:
            username_flag = check_username(user_name)
        except ValidationError:
            username_flag = True

        if not username_flag and not email_flag and not password_flag and password_flag != "short":
            # Entering data into Database (Register table)
            unique_id = uuid.uuid4().hex[:8]
            user = Users(unique_id, user_name, email, password, is_farmer)
            db.session.add(user)
            db.session.commit()
            session['user_id'] = user.id
            login_user(user)

            return redirect(url_for('check_login'))

    return render_template('sign-up.html',
                           email_flag=email_flag,
                           username_flag=username_flag,
                           password_flag=password_flag)


@app.route('/sign_in', methods=['GET', 'POST'])
def sign_in():
    if session.get("user_id"):
        return redirect(url_for('home'))
    flag = False
    if request.method == "POST":
        user = Users.query.filter_by(email=request.form['username']).first()
        if user is None:
            user = Users.query.filter_by(
                user_name=request.form['username']).first()
        if user is not None:
            if user.check_password(request.form['password']):
                user = Users.query.filter_by(email=user.email).first()
                session['user_id'] = user.id
                login_user(user)
                return redirect(url_for("home"))
            else:
                flag = True
        else:
            flag = True
    return render_template('sign-in.html', flag=flag)


@app.route("/logout")
@login_required
def logout():
    session.pop('user_id', None)
    logout_user()
    return redirect(url_for("home"))


@app.route('/contact_us', methods=["GET", "POST"])
def contact_us():
    if request.method == "POST":
        name = request.form['txtName']
        email = request.form['txtEmail']
        phone = request.form['txtPhone']
        msg = request.form['txtMsg']
        send_mail(name, email, phone, msg)
    if not session.get('user_id'):
        return render_template('contact-us.html')
    else:
        return render_template('contact-us.html',
                               unique_id=Users.query.filter_by(
                                   id=session.get('user_id')).first().unique_id,
                               is_farmer=Users.query.filter_by(id=session.get('user_id')).first().is_farmer)


@app.route('/about_us')
def about_us():
    if not session.get('user_id'):
        return render_template('about-us.html')
    else:
        return render_template('about-us.html',
                               unique_id=Users.query.filter_by(
                                   id=session.get('user_id')).first().unique_id,
                               is_farmer=Users.query.filter_by(id=session.get('user_id')).first().is_farmer)


@app.errorhandler(404)
def page_not_found(error):
    return render_template('404.html'), 404


@app.errorhandler(403)
def page_not_found(error):
    return render_template('403.html'), 403


# Functions
def check_mail(data):
    if Users.query.filter_by(email=data).first():
        raise ValidationError('Your email is already registered.')
    else:
        return False


def check_username(data):
    if Users.query.filter_by(user_name=data).first():
        raise ValidationError('This username is already registered.')
    else:
        return False


def check_password(data):
    special_char = string.punctuation
    if len(data) < 6:
        return "short"
    elif not re.search("[a-zA-Z]", data):
        return True
    elif not re.search("[0-9]", data):
        return True
    for char in data:
        if char in special_char:
            break
    else:
        return True
    return False


if __name__ == '__main__':
    app.run()
