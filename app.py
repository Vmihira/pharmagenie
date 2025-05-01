from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from pymongo import MongoClient
from bson import ObjectId
import os
import json
import math

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Replace with your actual connection string
MONGO_URI = "mongodb+srv://vinjamurimihira:Vmihira2004@cluster0.di7rite.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"


client = MongoClient(MONGO_URI)
db = client['askmebot']
users = db['users']

app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    SESSION_COOKIE_SECURE=True,  # Set True when running under HTTPS
)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/services/')
def services():
    return render_template('services.html')

@app.route('/services/<username>')
def services_render(username):
    return render_template('services.html', username=username)

@app.route('/user/register', methods=['GET', 'POST'])
def user_register():
    if request.method == 'POST':
        users = db.users
        if users.find_one({'email': request.form['email']}) is None:
            hashed = generate_password_hash(request.form['password'])
            users.insert_one({
                'name': request.form['name'],
                'email': request.form['email'],
                'username': request.form['email'][:-10],
                'password': hashed,
                'user_type': 'user',
                'medicines_fs': [],
                'medicines_sold': []
            })
            return redirect(url_for('user_login'))
        return 'Email already registered', 400
    return render_template('user_register.html')

@app.route('/user/login', methods=['GET', 'POST'])
def user_login():
    if request.method == 'POST':
        users = db.users
        login_user = users.find_one({'email': request.form['email']})
        if login_user and check_password_hash(login_user['password'], request.form['password']):
            session['user_id'] = str(login_user['_id'])
            session['user_type'] = login_user['user_type']
            session.permanent = False
            return redirect(url_for('user_dashboard', username=login_user['username']))
        return 'Invalid email/password combination', 401
    return render_template('user_login.html')

@app.route('/user/dashboard/<username>')
def user_dashboard(username):
    if session.get('user_id') and session.get('user_type') == 'user':
        return render_template('user_dashboard.html', username=username)
    return redirect(url_for('user_login'))

@app.route('/user/sell_medicine/<username>', methods=['GET', 'POST'])
def sell_medicine(username):
    if session.get('user_id') and session.get('user_type') == 'user':
        users = db.users
        if request.method == 'POST':
            count = int(request.form['count'])
            price = int(request.form['price'])
            medicine_data = {
                'user_id': session['user_id'],
                'name': request.form['name'],
                'medicine_name': request.form['medicine_name'],
                'price': math.floor((price * count) * 0.25)
            }
            users.update_one(
                {'username': username},
                {'$push': {'medicines_fs': medicine_data}}
            )
            return redirect(url_for('map_view', username=username))
        return render_template('sell_medicine.html', username=username)
    return redirect(url_for('user_login'))

@app.route('/map_view/<username>')
def map_view(username):
    if session.get('user_id') and session.get('user_type') == 'user':
        users = db.users
        user_doc = users.find_one({'username': username})
        medicine_listing = user_doc.get('medicines_fs', [])
        shops = list(users.find({'user_type': 'owner'}))
        for shop in shops:
            shop['_id'] = str(shop['_id'])
        return render_template(
            'map_view.html',
            medicine=medicine_listing,
            shops=json.dumps(shops),
            username=username
        )
    return redirect(url_for('user_login'))

@app.route('/map_view_owner/<username>')
def map_view_owners(username):
    users = db.users
    shops = list(users.find({'user_type': 'owner'}))
    for shop in shops:
        shop['_id'] = str(shop['_id'])
    return render_template(
        'map_view_owners.html',
        shops=json.dumps(shops),
        username=username
    )

@app.route('/shop_details/<shop_id>/<username>')
def shop_details(shop_id, username):
    if session.get('user_id') and session.get('user_type') == 'user':
        users = db.users
        user_doc = users.find_one({'username': username})
        listing = user_doc.get('medicines_fs', [])
        shop = users.find_one({'_id': ObjectId(shop_id), 'user_type': 'owner'})
        return render_template(
            'shop_details.html',
            shop=shop,
            medicines=listing,
            username=username
        )
    return redirect(url_for('user_login'))

@app.route('/resell_medicine/<owner_username>/<user_username>/<medicine_name>')
def resell_medicine(owner_username, user_username, medicine_name):
    if session.get('user_id') and session.get('user_type') == 'user':
        add_owner_list(owner_username, f"{user_username} {medicine_name}")
        return render_template('resell_success.html', username=user_username)
    return redirect(url_for('user_login'))

@app.route('/owner/accepted/<owner_username>/<user_username>')
def owner_accepted(owner_username, user_username):
    remove_owner_list(owner_username, user_username)
    return 'Accepted sell request Successfully'

@app.route('/sell_requests/<owner_username>')
def sell_requests(owner_username):
    users = db.users
    owner = users.find_one({'username': owner_username})
    return render_template(
        'owner_waitlist.html',
        sell_requests=owner.get('sell_requests', []),
        owner_username=owner_username
    )

@app.route('/medicines_bought/<owner_username>')
def medicines_bought(owner_username):
    users = db.users
    owner = users.find_one({'username': owner_username})
    return render_template(
        'owner_bought.html',
        medi_bought=owner.get('medicines_bought', []),
        owner_username=owner_username
    )

@app.route('/medicines_sold/<user_username>')
def medicines_sold(user_username):
    users = db.users
    user = users.find_one({'username': user_username})
    return render_template(
        'user_sold.html',
        medi_sold=user.get('medicines_sold', []),
        owner_username=user_username
    )

# Helper functions

def add_owner_list(owner_username, entry):
    db.users.update_one(
        {'username': owner_username},
        {'$push': {'sell_requests': entry}}
    )


def remove_owner_list(owner_username, user_entry):
    db.users.update_one(
        {'username': owner_username},
        {'$pull': {'sell_requests': user_entry}}
    )
    db.users.update_one(
        {'username': owner_username},
        {'$push': {'medicines_bought': user_entry}}
    )
    user_name = user_entry.split()[0]
    db.users.update_one(
        {'username': user_name},
        {'$push': {'medicines_sold': f"{owner_username} {user_name}"}}
    )

@app.route('/owner/register', methods=['GET', 'POST'])
def owner_register():
    if request.method == 'POST':
        users = db.users
        if users.find_one({'email': request.form['email']}) is None:
            hashed = generate_password_hash(request.form['password'])
            users.insert_one({
                'name': request.form['name'],
                'email': request.form['email'],
                'username': request.form['email'][:-10],
                'password': hashed,
                'user_type': 'owner',
                'shop_name': request.form['shop_name'],
                'latitude': request.form['latitude'],
                'longitude': request.form['longitude'],
                'sell_requests': [],
                'medicines_bought': []
            })
            return redirect(url_for('owner_login'))
        return 'Email already registered', 400
    return render_template('owner_register.html')

@app.route('/owner/login', methods=['GET', 'POST'])
def owner_login():
    if request.method == 'POST':
        users = db.users
        login_owner = users.find_one({'email': request.form['email'], 'user_type': 'owner'})
        if login_owner and check_password_hash(login_owner['password'], request.form['password']):
            session['user_id'] = str(login_owner['_id'])
            session['user_type'] = login_owner['user_type']
            return redirect(url_for('owner_dashboard', username=login_owner['username']))
        return 'Invalid email/password combination', 401
    return render_template('owner_login.html')

@app.route('/owner/dashboard/<username>')
def owner_dashboard(username):
    if session.get('user_id') and session.get('user_type') == 'owner':
        return render_template('owner_dashboard.html', username=username)
    return redirect(url_for('owner_login'))

@app.route('/get_current_location', methods=['POST'])
def get_current_location():
    data = request.json
    return jsonify({
        'latitude': data.get('latitude'),
        'longitude': data.get('longitude')
    })

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/contactus/')
def contactus():
    return render_template('contactus.html')

@app.route('/contactus/<username>')
def contactus_render(username):
    return render_template('contactus.html', username=username)

@app.route('/user/terms_conditions')
def user_terms_conditions():
    return render_template('user_terms.html')

@app.route('/owner/terms_conditions')
def owner_terms_conditions():
    return render_template('owner_terms.html')

if __name__ == '__main__':
    app.run(debug=True)
