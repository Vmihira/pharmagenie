from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_pymongo import PyMongo
from werkzeug.security import generate_password_hash, check_password_hash
from bson import ObjectId
import os
from pymongo import MongoClient
import json
import math

app = Flask(__name__)
app.secret_key = os.urandom(24)
urls = "mongodb+srv://kskkoushik135:LQCFjoGmTHFyIdRi@cluster0.zzxbiby.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
mongo = MongoClient(urls)

app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    SESSION_COOKIE_SECURE=True,  # Ensure this is only True if you are using HTTPS
)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/services/')
def services():
    return render_template('services.html')

@app.route('/services/<username>')
def services_render(username):
    return render_template('services.html' , username = username)

@app.route('/user/register', methods=['GET', 'POST'])
def user_register():
    if request.method == 'POST':
        users = mongo.db.users
        existing_user = users.find_one({'email': request.form['email']})
        if existing_user is None:
            hashpass = generate_password_hash(request.form['password'])
            users.insert_one({
                'name': request.form['name'],
                'email': request.form['email'],
                'username' : request.form['email'][0:-10],
                'password': hashpass,
                'user_type': 'user',
                'medicines_fs' : [] ,
                'medicines_sold' : []
            })
            return redirect(url_for('user_login'))
        return 'Email already registered'
    return render_template('user_register.html')

@app.route('/user/login', methods=['GET', 'POST'])
def user_login():
    if request.method == 'POST':
        users = mongo.db.users
        email = request.form['email']
        login_user = users.find_one({'email': email})
        if login_user:
            if check_password_hash(login_user['password'], request.form['password']):
                session['user_id'] = str(login_user['_id'])
                session['user_type'] = login_user['user_type']
                session.permanent = False
                return redirect(url_for('user_dashboard' ,username = email[0:-10]  ))
        return 'Invalid email/password combination'
    return render_template('user_login.html')

@app.route('/user/dashboard/<username>')
def user_dashboard(username):
    if 'user_id' in session and session['user_type'] == 'user':
        return render_template('user_dashboard.html' , username = username)
    return redirect(url_for('user_login'))

@app.route('/user/sell_medicine/<username>', methods=['GET', 'POST'])
def sell_medicine(username):
    if 'user_id' in session and session['user_type'] == 'user':
        users = mongo.db.users
        if request.method == 'POST':
            medicne_count = request.form['count']
            medicine_price = request.form['price']
            medicine_data = {
                'user_id': session['user_id'],
                'name': request.form['name'],
                'medicine_name': request.form['medicine_name'],
                'price': math.floor(((int(medicine_price)*int(medicne_count))/100)*25)
            }
            users.update_one({'username': username}, {"$push": {"medicines_fs": medicine_data }})
            return redirect(url_for('map_view' , username = username))
        return render_template('sell_medicine.html' , username = username)
    return redirect(url_for('user_login'))

@app.route('/map_view/<username>')
def map_view(username):
    if 'user_id' in session and session['user_type'] == 'user':
        users = mongo.db.users
        temp = users.find_one({'username': username})
        medicine_listing = temp['medicines_fs']
        shops = list(mongo.db.users.find({'user_type': 'owner'}))
        for shop in shops:
            shop['_id'] = str(shop['_id'])
        print('-------------------------------------------------------------')
        print(shops)  
        shops = json.dumps(shops)  
        return render_template('map_view.html', medicine=medicine_listing, shops = shops , username = username)
    return redirect(url_for('user_login'))

@app.route('/map_view_owner/<username>')
def map_view_owners(username):
   
        users = mongo.db.users
        shops = list(mongo.db.users.find({'user_type': 'owner'}))
        for shop in shops:
            shop['_id'] = str(shop['_id'])
        print('-------------------------------------------------------------')
        print(shops)  
        shops = json.dumps(shops)  
        return render_template('map_view_owners.html',  shops = shops , username = username)
  


@app.route('/shop_details/<shop_id>/<username>')
def shop_details(shop_id , username):
    if 'user_id' in session and session['user_type'] == 'user':
        users = mongo.db.users
        temp = users.find_one({'username': username})
        medicine_listing = temp['medicines_fs']
        shop = mongo.db.users.find_one({'_id': ObjectId(shop_id), 'user_type': 'owner'})
        return render_template('shop_details.html', shop=shop , medicines=medicine_listing , username = username)
    return redirect(url_for('user_login'))

@app.route('/resell_medicine/<owner_username>/<user_username>/<medicine_name>')
def resell_medicine(owner_username, user_username , medicine_name):
    if 'user_id' in session and session['user_type'] == 'user':
        add_owner_list(owner_username , user_username + " " + medicine_name)
        return render_template('resell_success.html' , username = user_username)
    return redirect(url_for('user_login'))

@app.route('/owner/accepted/<owner_username>/<user_username>')
def owner_accepted(owner_username, user_username):
    remove_owner_list(owner_username , user_username)
    return 'Accepted sell request Successfully'

@app.route('/sell_requests/<owner_username>')
def sell_requests(owner_username):
   
        users = mongo.db.users
        owner = users.find_one({'username': owner_username})
        sell_requests = owner['sell_requests']
        return render_template('owner_waitlist.html', sell_requests=sell_requests , owner_username = owner_username)

@app.route('/medicines_bought/<owner_username>')
def medicines_bought(owner_username):
   
        users = mongo.db.users
        owner = users.find_one({'username': owner_username})
        medi_bought = owner['medicines_bought']
        return render_template('owner_bought.html', medi_bought = medi_bought , owner_username = owner_username)

@app.route('/medicines_sold/<user_username>')
def medicines_sold(user_username):
   
        users = mongo.db.users
        owner = users.find_one({'username': user_username})
        medi_sold = owner['medicines_sold']
        return render_template('user_sold.html', medi_sold = medi_sold , owner_username = user_username)
            

def add_owner_list(owner_username , user_username):
    users = mongo.db.users
    users.update_one({'username': owner_username}, {"$push": {"sell_requests": user_username}})
    
def remove_owner_list(owner_username , user_username):
    users = mongo.db.users
    users.update_one({'username': owner_username}, {"$pull": {"sell_requests": user_username}})
    users.update_one({'username': owner_username}, {"$push": {"medicines_bought": user_username}})
    users.update_one({'username': user_username.split()[0]}, {"$push": {"medicines_sold" : owner_username + ' ' + user_username.split()[0]}})


@app.route('/owner/register', methods=['GET', 'POST'])
def owner_register():
    if request.method == 'POST':
        owners = mongo.db.users
        existing_owner = owners.find_one({'email': request.form['email']})
        if existing_owner is None:
            email = request.form['email']
            hashpass = generate_password_hash(request.form['password'])
            owners.insert_one({
                'name': request.form['name'],
                'email': email,
                'password': hashpass,
                'user_type': 'owner',
                'shop_name': request.form['shop_name'],
                'latitude': request.form['latitude'],
                'longitude': request.form['longitude'],
                'username': email[0:-10],
                'sell_requests' : [] ,
                'medicines_bought': []
            })
            return redirect(url_for('owner_login'))
        return 'Email already registered'
    return render_template('owner_register.html')

@app.route('/owner/login', methods=['GET', 'POST'])
def owner_login():
    if request.method == 'POST':
        owners = mongo.db.users
        email = request.form['email']
        login_owner = owners.find_one({'email': email, 'user_type': 'owner'})
        if login_owner:
            if check_password_hash(login_owner['password'], request.form['password']):
                session['user_id'] = str(login_owner['_id'])
                session['user_type'] = login_owner['user_type']
                return redirect(url_for('owner_dashboard' , username = email[0:-10]))
        return 'Invalid email/password combination'
    return render_template('owner_login.html')

@app.route('/owner/dashboard/<username>')
def owner_dashboard(username):
    if 'user_id' in session and session['user_type'] == 'owner':
        return render_template('owner_dashboard.html' , username = username)
    return redirect(url_for('owner_login'))



@app.route('/get_current_location', methods=['POST'])
def get_current_location():
    latitude = request.json['latitude']
    longitude = request.json['longitude']
    return jsonify({'latitude': latitude, 'longitude': longitude})

@app.route('/logout')
def logout():
     session['user_type'] = 'homepage'
     return render_template('index.html')

@app.route('/contactus/')
def contactus():
    return render_template('contactus.html')

@app.route('/contactus/<username>')
def contactus_render(username):
    return render_template('contactus.html' , username = username)

@app.route('/user/terms_conditions')
def user_terms_conditions():
    return render_template('user_terms.html')

@app.route('/owner/terms_conditions')
def owner_terms_conditions():
    return render_template('owner_terms.html')

if __name__ == '__main__':
    app.run(debug=True)