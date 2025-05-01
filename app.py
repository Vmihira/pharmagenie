from flask import Flask, render_template, request, redirect, url_for, session, jsonify # Removed flash
from werkzeug.security import generate_password_hash, check_password_hash
from pymongo import MongoClient, errors # Added errors for exception handling
from bson import ObjectId
import os
import json
import math

app = Flask(__name__)
# It's highly recommended to load the secret key from environment variables or a config file
app.secret_key = os.environ.get('FLASK_SECRET_KEY', os.urandom(24))

# --- Configuration ---
MONGO_URI = os.environ.get("MONGO_URI", "mongodb+srv://vinjamurimihira:Vmihira2004@askmebot.y3tx6.mongodb.net/?retryWrites=true&w=majority&appName=AskMeBot")

# Configure session cookie settings
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    SESSION_COOKIE_SECURE=request.is_secure, # Dynamically set based on request
)

# --- Database Setup ---
try:
    client = MongoClient(MONGO_URI)
    client.admin.command('ping')
    db = client['askmebot'] # Use your actual database name
    users_collection = db['users'] # Use a consistent variable for the collection
    print("Successfully connected to MongoDB.")
except errors.ConnectionFailure as e:
    print(f"Could not connect to MongoDB: {e}")
    exit()
except Exception as e:
    print(f"An error occurred during MongoDB setup: {e}")
    exit()


# --- Helper Functions (Reverted to original names and logic structure) ---

def add_owner_list(owner_username, entry):
    """Adds a sell request entry ('user_username medicine_name') to the owner's document."""
    # Note: No error handling in original, added basic try/except
    try:
        users_collection.update_one(
            {'username': owner_username, 'user_type': 'owner'}, # Ensure targeting owner
            {'$push': {'sell_requests': entry}}
        )
        return True # Original didn't explicitly return success/failure
    except errors.PyMongoError as e:
        print(f"Database error in add_owner_list for {owner_username}: {e}")
        return False


def remove_owner_list(owner_username, user_entry):
    """
    Processes an accepted sell request based on the original logic:
    1. Removes the request from the owner's 'sell_requests'.
    2. Adds the request to the owner's 'medicines_bought'.
    3. Adds a corresponding entry to the user's 'medicines_sold'.
    4. **Crucially, the original logic DID NOT remove the medicine from the user's 'medicines_fs' list.**
       This behavior is preserved here.
    Args:
        owner_username (str): The username of the owner.
        user_entry (str): The entry from the sell_requests list, expected format "user_username medicine_name".
    """
    # Note: No error handling in original, added basic try/except
    try:
        # 1. Pull from owner's sell_requests
        pull_result = users_collection.update_one(
            {'username': owner_username, 'user_type': 'owner'},
            {'$pull': {'sell_requests': user_entry}}
        )
        # Original code didn't check if pull was successful, proceeding regardless.

        # 2. Push to owner's medicines_bought
        users_collection.update_one(
            {'username': owner_username, 'user_type': 'owner'},
            {'$push': {'medicines_bought': user_entry}}
        )

        # 3. Push to user's medicines_sold (using original logic)
        # Original logic assumes user_entry contains "user_username medicine_name"
        # and extracts user_name from it to update the correct user.
        try:
            user_name = user_entry.split()[0]
            # Original format for medicines_sold entry
            sold_entry = f"{owner_username} {user_name}" # Original was "owner_username user_name"
            users_collection.update_one(
                {'username': user_name, 'user_type': 'user'}, # Target the user
                {'$push': {'medicines_sold': sold_entry}}
            )
        except IndexError:
             print(f"Error: Could not parse user_name from user_entry '{user_entry}' in remove_owner_list.")
             # Decide how to handle this - original code would likely raise an error here.

        # 4. Original logic did NOT remove from user's 'medicines_fs'.

        return True # Original didn't explicitly return

    except errors.PyMongoError as e:
        print(f"Database error in remove_owner_list for {owner_username} / {user_entry}: {e}")
        return False
    except Exception as e:
        print(f"Unexpected error in remove_owner_list: {e}")
        return False


# --- Routes ---

@app.route('/')
def index():
    """Renders the homepage."""
    return render_template('index.html')

@app.route('/services/')
def services():
    """Renders the services page (generic)."""
    username = session.get('username')
    return render_template('services.html', username=username)

# Original route - kept as is
@app.route('/services/<username>')
def services_render(username):
     # Assuming this is intended behavior from original code
    return render_template('services.html', username=username)

# --- User Authentication and Actions ---

@app.route('/user/register', methods=['GET', 'POST'])
def user_register():
    """Handles user registration."""
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')

        # Basic validation (keeping backend check)
        if not name or not email or not password:
            # Reverted: No flash message
            return 'All fields are required.', 400 # Example: return error text

        users = users_collection # Use consistent variable
        existing_user = users.find_one({'email': email})
        if existing_user:
            # Reverted: No flash message
            return 'Email already registered', 400 # Original response

        # Generate username (using original logic)
        username = email[:-10] # Original logic, kept despite fragility warning

        hashed_password = generate_password_hash(password)

        try:
            users.insert_one({
                'name': name,
                'email': email,
                'username': username,
                'password': hashed_password,
                'user_type': 'user',
                'medicines_fs': [], # Reverted field name
                'medicines_sold': []
            })
            # Reverted: No flash message
            return redirect(url_for('user_login')) # Original redirect
        except errors.PyMongoError as e:
            print(f"Database error during user registration: {e}")
            # Reverted: No flash message
            return 'Registration failed due to a server error.', 500

    return render_template('user_register.html')

@app.route('/user/login', methods=['GET', 'POST'])
def user_login():
    """Handles user login."""
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        if not email or not password:
             # Reverted: No flash message
            return 'Email and password are required.', 400

        users = users_collection
        login_user = users.find_one({'email': email, 'user_type': 'user'}) # Ensure user_type

        if login_user and check_password_hash(login_user['password'], password):
            session['user_id'] = str(login_user['_id'])
            session['user_type'] = login_user['user_type']
            session['username'] = login_user['username'] # Store username in session
            session.permanent = False # Original didn't set this, but it's good practice
            # Reverted: No flash message
            return redirect(url_for('user_dashboard', username=login_user['username']))
        else:
            # Reverted: No flash message
            return 'Invalid email/password combination', 401 # Original response

    return render_template('user_login.html')

@app.route('/user/dashboard/<username>')
def user_dashboard(username):
    """Displays the user dashboard."""
    # Enhanced auth check (backend only change, safe to keep)
    if session.get('user_type') == 'user' and session.get('username') == username:
        return render_template('user_dashboard.html', username=username)
    # Redirect if wrong user or not logged in (original behavior implicitly did this)
    # Reverted: No flash messages on redirect
    elif session.get('user_id'):
         # Logged in, but wrong user's dashboard - redirect to their own
         return redirect(url_for('user_dashboard', username=session['username']))
    else:
        # Not logged in
        return redirect(url_for('user_login'))

@app.route('/user/sell_medicine/<username>', methods=['GET', 'POST'])
def sell_medicine(username):
    """Handles the form for users to list medicine for sale."""
    # Enhanced auth check (backend only change, safe to keep)
    if not (session.get('user_type') == 'user' and session.get('username') == username):
        # Reverted: No flash message
        return redirect(url_for('user_login'))

    if request.method == 'POST':
        try:
            # Use original form field names if they were different
            count_str = request.form.get('count')
            price_str = request.form.get('price')
            medicine_name = request.form.get('medicine_name')
            user_name = request.form.get('name') # Assuming 'name' was the field for user's name

            # Basic validation
            if not count_str or not price_str or not medicine_name or not user_name:
                # Reverted: No flash
                return "Missing required fields", 400

            count = int(count_str)
            price = int(price_str) # Assuming this is original price per item

            if count <= 0 or price <= 0:
                 # Reverted: No flash
                 return "Count and price must be positive numbers", 400

            # Original calculation logic
            calculated_price = math.floor((price * count) * 0.25)

            # Original data structure for the medicine entry
            medicine_data = {
                # Original didn't add ObjectId, relying on position/content
                'user_id': session['user_id'], # Original had this
                'name': user_name, # Original field name was 'name'
                'medicine_name': medicine_name, # Original field name
                'price': calculated_price # Original field name was 'price'
                # Original did NOT store count, original_price, or status
            }

            users = users_collection
            result = users.update_one(
                {'username': username, 'user_type': 'user'},
                {'$push': {'medicines_fs': medicine_data}} # Reverted field name
            )

            if result.modified_count > 0:
                 # Reverted: No flash message
                return redirect(url_for('map_view', username=username)) # Original redirect
            else:
                 # Reverted: No flash message
                # Provide a generic error or redirect back
                print(f"Failed to update medicines_fs for user {username}")
                return "Failed to list medicine", 500 # Or redirect

        except ValueError:
             # Reverted: No flash message
            return 'Invalid number format for count or price.', 400
        except errors.PyMongoError as e:
            print(f"Database error listing medicine for {username}: {e}")
             # Reverted: No flash message
            return 'Failed to list medicine due to a server error.', 500

    # GET request
    return render_template('sell_medicine.html', username=username)

@app.route('/map_view/<username>')
def map_view(username):
    """Displays map with shops and the user's medicines for sale."""
    # Enhanced auth check (backend only change, safe to keep)
    if not (session.get('user_type') == 'user' and session.get('username') == username):
        # Reverted: No flash message
        return redirect(url_for('user_login'))

    try:
        users = users_collection
        user_doc = users.find_one({'username': username, 'user_type': 'user'})
        if not user_doc:
             # Reverted: No flash message
            print(f"User not found in map_view: {username}")
            return redirect(url_for('user_login')) # Or handle differently

        # Get medicines using original field name, no status filtering
        medicine_listing = user_doc.get('medicines_fs', []) # Reverted field name

        # Fetch shops (owners)
        shops_cursor = users.find({'user_type': 'owner'})
        shops_list = list(shops_cursor)

        # Prepare shops data for template (keep password removal and ID conversion)
        for shop in shops_list:
            shop['_id'] = str(shop['_id'])
            shop.pop('password', None) # Keep this security fix

        return render_template(
            'map_view.html',
            medicine=medicine_listing, # Original template variable name was 'medicine'
            shops=json.dumps(shops_list),
            username=username
        )
    except errors.PyMongoError as e:
        print(f"Database error fetching map data for {username}: {e}")
        # Reverted: No flash message
        # Redirect or show error page
        return "Error loading map data.", 500 # Example error response

# Original route - kept as is
@app.route('/map_view_owner/<username>')
def map_view_owners(username):
     # Original code didn't have auth check here, adding it is safer but deviates.
     # Reverting to NO auth check to match original exactly.
     # if not (session.get('user_type') == 'owner' and session.get('username') == username):
     #    return redirect(url_for('owner_login'))

    try:
        users = users_collection
        shops_cursor = users.find({'user_type': 'owner'})
        shops_list = list(shops_cursor)
        for shop in shops_list:
            shop['_id'] = str(shop['_id'])
            shop.pop('password', None) # Keep this security fix

        return render_template(
            'map_view_owners.html', # Assuming this template exists
            shops=json.dumps(shops_list),
            username=username
        )
    except errors.PyMongoError as e:
        print(f"Database error fetching owner map data: {e}")
        return "Error loading map data.", 500

# Original route - kept as is
@app.route('/shop_details/<shop_id>/<username>')
def shop_details(shop_id, username):
    # Enhanced auth check (backend only change, safe to keep)
    if not (session.get('user_type') == 'user' and session.get('username') == username):
        # Reverted: No flash message
        return redirect(url_for('user_login'))

    try:
        users = users_collection
        # Validate shop_id format (keeping this improvement)
        try:
            shop_object_id = ObjectId(shop_id)
        except Exception:
            # Reverted: No flash message
            return "Invalid shop ID format.", 400 # Example error

        shop = users.find_one({'_id': shop_object_id, 'user_type': 'owner'})
        if not shop:
             # Reverted: No flash message
            return "Shop not found.", 404 # Example error

        user_doc = users.find_one({'username': username, 'user_type': 'user'})
        if not user_doc:
             # Reverted: No flash message
            print(f"User not found in shop_details: {username}")
            return redirect(url_for('user_login')) # Or handle differently

        # Get user's medicines using original field name, no status filtering
        user_medicines = user_doc.get('medicines_fs', []) # Reverted field name

        # Prepare shop data (keep password removal and ID conversion)
        shop.pop('password', None)
        shop['_id'] = str(shop['_id'])

        return render_template(
            'shop_details.html', # Assuming this template exists
            shop=shop,
            medicines=user_medicines, # Original template variable name was 'medicines'
            username=username
        )
    except errors.PyMongoError as e:
        print(f"Database error fetching shop details: {e}")
        # Reverted: No flash message
        return "Error loading shop details.", 500

# Original route - kept as is, using original helper function
@app.route('/resell_medicine/<owner_username>/<user_username>/<medicine_name>')
def resell_medicine(owner_username, user_username, medicine_name):
    # Enhanced auth check (backend only change, safe to keep)
    if not (session.get('user_type') == 'user' and session.get('username') == user_username):
         # Reverted: No flash message
        return redirect(url_for('user_login')) # Or deny access

    # Original code didn't explicitly check if medicine exists in user's list first.
    # It directly called add_owner_list. Reverting to that behavior.

    # Create the entry for the owner's request list (original format)
    sell_request_entry = f"{user_username} {medicine_name}"

    # Use the original helper function name
    if add_owner_list(owner_username, sell_request_entry):
        # Original code just rendered success template without flash
        # Original code did NOT update medicine status to pending
        return render_template('resell_success.html', username=user_username) # Ensure resell_success.html exists
    else:
         # Reverted: No flash message
        # Handle failure - maybe redirect back or show error
        print(f"Failed to add sell request via add_owner_list for {owner_username}")
        return "Failed to send sell request.", 500 # Example


# --- Owner Actions (Accepting Sell) ---

# Route for owner accepting - adjusted to use original helper `remove_owner_list`
# NOTE: The original route signature /owner/accepted/<owner_username>/<user_username> was insufficient
# because remove_owner_list needs the full entry ("user_username medicine_name").
# Keeping the <path:sell_request_entry> from the *updated* code is necessary for the logic to work
# based on how sell requests are stored. Assuming the frontend *can* provide this full entry.
@app.route('/owner/accepted/<owner_username>/<path:sell_request_entry>')
def owner_accepted(owner_username, sell_request_entry):
    """Handles the owner accepting a sell request using original logic structure."""
    # Enhanced auth check (backend only change, safe to keep)
    if not (session.get('user_type') == 'owner' and session.get('username') == owner_username):
        # Reverted: No flash message
        return redirect(url_for('owner_login')) # Or deny access

    # Use the original helper function name, passing the full entry
    if remove_owner_list(owner_username, sell_request_entry):
        # Original code returned simple text
        return 'Accepted sell request Successfully'
    else:
        # Reverted: No flash message
        print(f"Failed to process acceptance via remove_owner_list for {owner_username}/{sell_request_entry}")
        # Return an error or redirect
        return 'Failed to process acceptance.', 500 # Example

# Original route - kept as is
@app.route('/sell_requests/<owner_username>')
def sell_requests(owner_username):
    # Auth check (safer, but not in original - keeping it)
    if not (session.get('user_type') == 'owner' and session.get('username') == owner_username):
        return redirect(url_for('owner_login'))

    try:
        users = users_collection
        owner = users.find_one({'username': owner_username, 'user_type': 'owner'})
        if not owner:
             # Reverted: No flash message
            return "Owner not found.", 404

        return render_template(
            'owner_waitlist.html', # Ensure this template exists
            sell_requests=owner.get('sell_requests', []),
            owner_username=owner_username
        )
    except errors.PyMongoError as e:
        print(f"Database error fetching sell requests for {owner_username}: {e}")
        # Reverted: No flash message
        return "Error loading sell requests.", 500

# Original route - kept as is
@app.route('/medicines_bought/<owner_username>')
def medicines_bought(owner_username):
     # Auth check (safer, but not in original - keeping it)
    if not (session.get('user_type') == 'owner' and session.get('username') == owner_username):
        return redirect(url_for('owner_login'))

    try:
        users = users_collection
        owner = users.find_one({'username': owner_username, 'user_type': 'owner'})
        if not owner:
            # Reverted: No flash message
            return "Owner not found.", 404

        return render_template(
            'owner_bought.html', # Ensure this template exists
            medi_bought=owner.get('medicines_bought', []),
            owner_username=owner_username
        )
    except errors.PyMongoError as e:
        print(f"Database error fetching bought medicines for {owner_username}: {e}")
         # Reverted: No flash message
        return "Error loading bought medicines.", 500

# Original route - kept as is
@app.route('/medicines_sold/<user_username>')
def medicines_sold(user_username):
    # Auth check (safer, but not in original - keeping it)
    if not (session.get('user_type') == 'user' and session.get('username') == user_username):
        return redirect(url_for('user_login'))

    try:
        users = users_collection
        user = users.find_one({'username': user_username, 'user_type': 'user'})
        if not user:
             # Reverted: No flash message
            return "User not found.", 404

        return render_template(
            'user_sold.html', # Ensure this template exists
            # Original template variable name was 'medi_sold'
            medi_sold=user.get('medicines_sold', []),
            # Original template variable name was 'owner_username', changing to 'username' for consistency
            username=user_username
        )
    except errors.PyMongoError as e:
        print(f"Database error fetching sold medicines for {user_username}: {e}")
         # Reverted: No flash message
        return "Error loading sold medicines.", 500

# --- Owner Authentication ---

@app.route('/owner/register', methods=['GET', 'POST'])
def owner_register():
    """Handles owner (shop) registration."""
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        shop_name = request.form.get('shop_name')
        latitude = request.form.get('latitude')
        longitude = request.form.get('longitude')

        # Basic validation (keeping backend check)
        if not name or not email or not password or not shop_name or not latitude or not longitude:
             # Reverted: No flash message
            return 'All fields are required.', 400

        # Validate coordinates (keeping this improvement)
        try:
            float(latitude)
            float(longitude)
        except ValueError:
             # Reverted: No flash message
            return 'Invalid format for latitude or longitude.', 400

        users = users_collection
        existing_user = users.find_one({'email': email})
        if existing_user:
             # Reverted: No flash message
            return 'Email already registered', 400 # Original response

        # Generate username (using original logic)
        username = email[:-10] if '@' in email and len(email) > 10 else email.split('@')[0]
        hashed_password = generate_password_hash(password)

        try:
            users.insert_one({
                'name': name,
                'email': email,
                'username': username,
                'password': hashed_password,
                'user_type': 'owner',
                'shop_name': shop_name,
                'latitude': latitude, # Keep as string like original
                'longitude': longitude, # Keep as string like original
                'sell_requests': [],
                'medicines_bought': []
            })
             # Reverted: No flash message
            return redirect(url_for('owner_login')) # Original redirect
        except errors.PyMongoError as e:
            print(f"Database error during owner registration: {e}")
             # Reverted: No flash message
            return 'Registration failed due to a server error.', 500

    return render_template('owner_register.html')

@app.route('/owner/login', methods=['GET', 'POST'])
def owner_login():
    """Handles owner (shop) login."""
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        if not email or not password:
             # Reverted: No flash message
            return 'Email and password are required.', 400

        users = users_collection
        login_owner = users.find_one({'email': email, 'user_type': 'owner'})

        if login_owner and check_password_hash(login_owner['password'], password):
            session['user_id'] = str(login_owner['_id'])
            session['user_type'] = login_owner['user_type']
            session['username'] = login_owner['username'] # Store username
            session.permanent = False # Keep this
             # Reverted: No flash message
            return redirect(url_for('owner_dashboard', username=login_owner['username']))
        else:
             # Reverted: No flash message
            return 'Invalid email/password combination', 401 # Original response

    return render_template('owner_login.html')

@app.route('/owner/dashboard/<username>')
def owner_dashboard(username):
    """Displays the owner dashboard."""
    # Enhanced auth check (backend only change, safe to keep)
    if session.get('user_type') == 'owner' and session.get('username') == username:
        return render_template('owner_dashboard.html', username=username)
    # Redirect if wrong user or not logged in
    # Reverted: No flash messages on redirect
    elif session.get('user_id'):
         return redirect(url_for('owner_dashboard', username=session['username']))
    else:
        return redirect(url_for('owner_login'))

# --- Other Routes (Kept mostly as original) ---

@app.route('/get_current_location', methods=['POST'])
def get_current_location():
    """Endpoint to potentially receive user's location (e.g., from browser JS)."""
    # Original code didn't have auth or extensive error checks here
    data = request.json
    # Original just returned the data, keeping basic structure
    return jsonify({
        'latitude': data.get('latitude'),
        'longitude': data.get('longitude')
    })


@app.route('/logout')
def logout():
    """Clears the session and redirects to homepage."""
    session.clear()
    # Reverted: No flash message
    return redirect(url_for('index')) # Original redirect

@app.route('/contactus/')
def contactus():
    """Renders the contact us page."""
    # Original didn't pass username here, reverting
    # username = session.get('username')
    return render_template('contactus.html') # Removed username=username

# Original route - kept as is
@app.route('/contactus/<username>')
def contactus_render(username):
    # Original passed username, keeping it
    return render_template('contactus.html', username=username)

# Original route - kept as is
@app.route('/user/terms_conditions')
def user_terms_conditions():
    """Renders user terms and conditions."""
    return render_template('user_terms.html') # Ensure this template exists

# Original route - kept as is
@app.route('/owner/terms_conditions')
def owner_terms_conditions():
    """Renders owner terms and conditions."""
    return render_template('owner_terms.html') # Ensure this template exists

# --- Main Execution ---
if __name__ == '__main__':
    # Use debug=True for development, False for production
    app.run(debug=True)
