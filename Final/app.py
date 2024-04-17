from flask import Flask, render_template, request, redirect, url_for, flash, session
import sqlite3
from werkzeug.utils import secure_filename
import os
import pytz
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'Team6IsHot'  # Change this to a secure random key

# Create a SQLite database connection
conn = sqlite3.connect('final.db')
cursor = conn.cursor()

@app.template_filter('datetimeformat')
def datetimeformat(value, format='%B %d, %Y %I:%M %p'):
    if value is None:
        return ""
    # Convert the string to a datetime object in UTC
    utc_time = datetime.strptime(value, '%Y-%m-%d %H:%M:%S').replace(tzinfo=pytz.utc)
    # Convert to Eastern Time
    eastern = pytz.timezone('US/Eastern')
    eastern_time = utc_time.astimezone(eastern)
    # Format the time with a leading zero for hours
    formatted_time = eastern_time.strftime(format)
    # Replace leading zero in hour for non-zero-padded hour format
    if formatted_time[0] == "0":
        formatted_time = formatted_time[1:]
    return formatted_time


def is_user_admin():
    # Modify this function to create a new connection to the database
    # whenever it is called, to ensure it is using a fresh connection.
    conn = sqlite3.connect('final.db')
    conn.row_factory = sqlite3.Row  # Set row factory to access columns by name
    cursor = conn.cursor()
    user_id = session.get('user_id')
    cursor.execute("SELECT is_admin FROM Users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()  # Close the connection after checking
    return result and result['is_admin'] == 1

@app.route('/')
@app.route('/home')
def home():
    conn = sqlite3.connect('final.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Fetch the top three users
    cursor.execute("""
        SELECT u.user_id, u.user_name, u.f_name, u.l_name, u.profile_image, AVG(r.rating) as avg_rating
        FROM Users u
        JOIN Review r ON u.user_id = r.reviewedUserID
        GROUP BY u.user_id
        ORDER BY avg_rating DESC
        LIMIT 3
    """)
    top_users = cursor.fetchall()
    conn.close()

    return render_template('home.html', top_users=top_users)

@app.route('/inbox')
def inbox():
    user_id = session.get('user_id')
    if user_id is None:
        return redirect(url_for('login'))

    conn = sqlite3.connect('final.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Fetch the current user's profile
    cursor.execute("SELECT * FROM Users WHERE user_id=?", (user_id,))
    user = cursor.fetchone()

    # Fetch all user profiles for the dropdown
    cursor.execute("SELECT user_id, user_name FROM Users WHERE user_id != ?", (user_id,))
    all_users = cursor.fetchall()

    # Fetch all conversations for the current user
    cursor.execute("""
        SELECT DISTINCT other.user_id, other.user_name,
        (SELECT content FROM Message WHERE (senderID = other.user_id AND receiverID = ?)
        OR (senderID = ? AND receiverID = other.user_id) ORDER BY sendDate DESC LIMIT 1) AS last_message
        FROM Users other
        JOIN Message ON other.user_id = Message.senderID OR other.user_id = Message.receiverID
        WHERE other.user_id != ?
        GROUP BY other.user_id, Message.sendDate
        ORDER BY Message.sendDate DESC
    """, (user_id, user_id, user_id))

    conversations = cursor.fetchall()
    conn.close()

    return render_template('inbox.html', user=user, all_users=all_users, conversations=conversations)

@app.route('/conversation')
def conversation():
    user_id = session.get('user_id')
    if user_id is None:
        return redirect(url_for('login'))

    with_user_id = request.args.get('with_user_id')
    if with_user_id is None:
        return redirect(url_for('inbox'))

    conn = sqlite3.connect('final.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Fetch the username of the conversation partner
    cursor.execute("SELECT user_name FROM Users WHERE user_id = ?", (with_user_id,))
    with_user = cursor.fetchone()

    # Make sure the conversation partner exists
    if with_user is None:
        return redirect(url_for('inbox'))

    # Fetch messages where the current user is either the sender or receiver
    cursor.execute("""
        SELECT m.*, u.user_name as sender_name
        FROM Message m
        JOIN Users u ON u.user_id = m.senderID
        WHERE (m.senderID = ? AND m.receiverID = ?) OR (m.senderID = ? AND m.receiverID = ?)
        ORDER BY m.sendDate ASC
    """, (user_id, with_user_id, with_user_id, user_id))

    messages = cursor.fetchall()
    conn.close()

    # Pass the username of the conversation partner to the template
    return render_template('conversation.html', user_id=user_id, messages=messages, with_user_id=with_user_id, with_user_name=with_user['user_name'])

@app.route('/send_message', methods=['POST'])
def send_message():
    user_id = session.get('user_id')
    if user_id is None:
        return redirect(url_for('login'))

    receiver_id = request.form.get('receiver_id')
    message_content = request.form.get('message_content')

    if receiver_id and message_content:
        conn = sqlite3.connect('final.db')
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO Message (senderID, receiverID, content, sendDate, isRead)
            VALUES (?, ?, ?, datetime('now'), 0)
        """, (user_id, receiver_id, message_content))

        conn.commit()
        conn.close()

    return redirect(url_for('conversation', with_user_id=receiver_id))

@app.route('/listings')
def listings():
    user_id = session.get('user_id')
    if user_id is None:
        return redirect(url_for('login'))

    category = request.args.get('category', None)
    search_query = request.args.get('search_query', '')

    # Fetch categories for the dropdown
    conn = sqlite3.connect('final.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM Category")
    categories = cursor.fetchall()

    search_condition = "%" + search_query + "%"  # Used for LIKE SQL operator

    # Build the base of the SQL query
    sql_query = """
        SELECT Listings.*, Category.name as category_name FROM Listings
        LEFT JOIN Category ON Listings.category = Category.name
    """

    # Apply filters based on category and search query if provided
    conditions = []
    params = []

    if category:
        conditions.append("Category.name = ?")
        params.append(category)

    if search_query:
        conditions.append("Listings.title LIKE ?")
        params.append(search_condition)

    if conditions:  # If there are any conditions, append them to the query
        sql_query += " WHERE " + " AND ".join(conditions)

    sql_query += " ORDER BY Listings.listing_id DESC"

    cursor.execute(sql_query, params)
    all_listings = cursor.fetchall()
    conn.close()

    return render_template('listings.html', listings=all_listings, categories=categories, selected_category=category, search_query=search_query)

@app.route('/create-listing')
def createlisting():
    user_id = session.get('user_id')
    if user_id is None:
        return redirect(url_for('login'))

    # Fetch categories from the database
    conn = sqlite3.connect('final.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Category")  # Assuming your table name is 'Category'
    categories = cursor.fetchall()
    conn.close()

    if user_id is None:
        return redirect(url_for('login'))

    # Pass categories to the template
    return render_template('create-listing.html', user=user_id, categories=categories)

@app.route('/delete_listing/<int:listing_id>', methods=['POST'])
def delete_listing(listing_id):
    if not session.get('user_id'):
        return redirect(url_for('login'))

    # Check if the user is an admin or the listing belongs to the user
    conn = sqlite3.connect('final.db')
    cursor = conn.cursor()

    if is_user_admin():
        # If the user is an admin, they can delete any listing
        cursor.execute("DELETE FROM Listings WHERE listing_id=?", (listing_id,))
    else:
        # If not an admin, check if the listing belongs to the user before deleting
        cursor.execute("SELECT * FROM Listings WHERE listing_id=? AND user_id=?", (listing_id, session['user_id']))
        listing = cursor.fetchone()
        if listing:
            cursor.execute("DELETE FROM Listings WHERE listing_id=?", (listing_id,))
        else:
            flash("You are not authorized to delete this listing.")
            return redirect(url_for('listings'))

    conn.commit()
    conn.close()
    flash("Listing deleted successfully.")
    return redirect(url_for('listings'))

@app.route('/submit-listing', methods=['POST'])
def submit_listing():
    user_id = session.get('user_id')
    if user_id is None:
        return redirect(url_for('login'))

    title = request.form['title']
    description = request.form['description']
    category = request.form['category']
    images = request.files.getlist('images')

    # Server-side validation for title and description length
    if len(title) > 50:
        flash('Title must be less than 50 characters.')
        return redirect(url_for('create_listing'))

    if len(description) > 250:
        flash('Description must be less than 250 characters.')
        return redirect(url_for('create_listing'))

    # Save images and get their file paths
    image_paths = []
    for image in images:
        if image and allowed_file(image.filename):
            # Check the image size
            image.seek(0, os.SEEK_END)  # Seek to the end of the file to get the size
            image_size = image.tell()  # Get the size of the file
            if image_size > 5 * 1024 * 1024:  # If the image size is greater than 5MB
                flash('Image file size must be less than 5MB.')
                return redirect(url_for('create_listing'))
            image.seek(0)  # Reset the file pointer to the start of the file

            filename = secure_filename(image.filename)
            directory = os.path.join(app.root_path, 'static/images/listings')
            if not os.path.exists(directory):
                os.makedirs(directory)
            filepath = os.path.join(directory, filename)
            image.save(filepath)
            image_paths.append('images/listings/' + filename)  # Make sure to use the correct relative path
        else:
            # If no file is selected or file is not allowed, flash a message
            flash('Please upload a valid image file.')
            return redirect(url_for('create_listing'))

    image_paths_str = ",".join(image_paths)

    # Insert listing into the database
    conn = sqlite3.connect('final.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO Listings (user_id, title, description, images, category) VALUES (?, ?, ?, ?, ?)", (user_id, title, description, image_paths_str, category))
    conn.commit()
    conn.close()

    flash('Listing created successfully!')
    return redirect(url_for('listings'))

@app.route('/listing/<int:listing_id>')
def listing_detail(listing_id):
    user_id = session.get('user_id')  # Get user_id from the session
    conn = sqlite3.connect('final.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT Listings.*, Users.user_name, Users.is_admin FROM Listings INNER JOIN Users ON Listings.user_id = Users.user_id WHERE Listings.listing_id=?", (listing_id,))
    listing = cursor.fetchone()
    conn.close()

    if listing is None:
        return redirect(url_for('listings'))

    # Set can_delete to True if the user is an admin or if they are the owner of the listing.
    can_delete = (user_id and (listing['user_id'] == user_id or is_user_admin()))

    return render_template('listing_detail.html', listing=listing, can_delete=can_delete)


@app.route('/registration')
def index():
    return render_template('register.html')

@app.route('/register', methods=['POST'])
def register():
    username = request.form['username']
    first = request.form['first']
    last = request.form['last']
    email = request.form['email']
    password = request.form['password']
    location = request.form['location']

    if not first.strip() or not last.strip() or not email.strip():
        flash('First name, last name, and email cannot be empty or just spaces.', 'register_error')
        return redirect(url_for('index'))

    if not username or not password:
        flash('Username and password are required', 'register_error')
        return redirect(url_for('index'))

    conn = sqlite3.connect('final.db')
    cursor = conn.cursor()

    # Here, add a check to see if the username already exists to prevent duplicate registrations
    cursor.execute("SELECT user_id FROM Users WHERE user_name=?", (username,))
    if cursor.fetchone():
        flash('Username already exists', 'register_error')
        return redirect(url_for('index'))  # Redirect back to registration page

    cursor.execute("SELECT user_id FROM Users WHERE email=?", (email,))
    if cursor.fetchone():
        flash('Email address already in use. Please use a different email address.', 'register_error')
        return redirect(url_for('index'))  # Redirect back to registration page

    hashed_password = generate_password_hash(password)
    cursor.execute("INSERT INTO Users (user_name, f_name, l_name, email, user_password, location) VALUES (?, ?, ?, ?, ?, ?)", (username, first, last, email, hashed_password, location))
    conn.commit()
    conn.close()

    return redirect(url_for('login'))  # Redirect to the login page

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if not username or not password:
            flash('Username and password are required', 'login_error')
            return redirect(url_for('login'))

        conn = sqlite3.connect('final.db')
        conn.row_factory = sqlite3.Row  # Set the row_factory to sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Users WHERE user_name=?", (username,))
        user = cursor.fetchone()

        if user is None or not check_password_hash(user['user_password'], password):
            flash('Invalid username or password', 'login_error')
            conn.close()
            return redirect(url_for('login'))
        else:
            # Update last login time
            now = datetime.now().strftime('%Y-%m-%d %I:%M:%S %p')
            cursor.execute("UPDATE Users SET lastLogin=? WHERE user_id=?", (now, user['user_id']))
            conn.commit()

            session['user_id'] = user['user_id']
            conn.close()
            return redirect(url_for('profile'))

    return render_template('login.html')

@app.route('/profile')
def profile():
    user_id = session.get('user_id')
    if user_id is None:
        return redirect(url_for('login'))

    conn = sqlite3.connect('final.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Users WHERE user_id=?", (user_id,))
    user = cursor.fetchone()

    if user is None:
        return redirect(url_for('login'))

    # Fetch the user's listings
    cursor.execute("SELECT * FROM Listings WHERE user_id=?", (user_id,))
    listings = cursor.fetchall()

     # Fetch the average review score for the profile user
    cursor.execute("SELECT AVG(rating) as average_rating FROM Review WHERE reviewedUserID=?", (user_id,))
    average_review = cursor.fetchone()
    average_rating = round(average_review['average_rating'], 1) if average_review['average_rating'] is not None else None

    conn.close()

    return render_template('profile.html', user=user, listings=listings, average_rating=average_rating, is_own_profile=True)

@app.route('/update_profile', methods=['POST'])
def update_profile():
    user_id = session.get('user_id')
    if user_id is None:
        return redirect(url_for('login'))

    # Get the form data
    username = request.form['username']
    email = request.form['email']
    location = request.form['location']
    profile_image = request.files['profile_image']

    # Connect to the database
    conn = sqlite3.connect('final.db')
    cursor = conn.cursor()

    # Check if the username is taken by another user
    cursor.execute("SELECT user_id FROM Users WHERE user_name=? AND user_id!=?", (username, user_id))
    if cursor.fetchone():
        flash('This username is already taken', 'profile_error')
        return redirect(url_for('profile'))

    # Check if the email is taken by another user
    cursor.execute("SELECT user_id FROM Users WHERE email=? AND user_id!=?", (email, user_id))
    if cursor.fetchone():
        flash('This email is already being used', 'profile_error')
        return redirect(url_for('profile'))

    # Process the profile image if it's provided
    if profile_image and allowed_file(profile_image.filename):
        filename = secure_filename(profile_image.filename)
        directory = os.path.join(app.root_path, 'static/images')
        if not os.path.exists(directory):
            os.makedirs(directory)
        filepath = os.path.join(directory, filename)
        profile_image.save(filepath)
        profile_image_url = 'images/' + filename
    else:
        profile_image_url = request.form['current_profile_image']

    # Update the user's profile
    cursor.execute("UPDATE Users SET user_name=?, email=?, location=?, profile_image=? WHERE user_id=?", (username, email, location, profile_image_url, user_id))
    conn.commit()
    conn.close()

    return redirect(url_for('profile'))

@app.route('/user/<int:user_id>')
def public_profile(user_id):
    conn = sqlite3.connect('final.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Fetch the profile user's information
    cursor.execute("SELECT * FROM Users WHERE user_id=?", (user_id,))
    profile_user = cursor.fetchone()

    if profile_user is None:
        return redirect(url_for('home'))

    # Fetch the profile user's listings
    cursor.execute("SELECT * FROM Listings WHERE user_id=?", (user_id,))
    listings = cursor.fetchall()

    # Fetch the average review score for the profile user
    cursor.execute("SELECT AVG(rating) as average_rating FROM Review WHERE reviewedUserID=?", (user_id,))
    average_review = cursor.fetchone()
    average_rating = round(average_review['average_rating'], 1) if average_review['average_rating'] is not None else None

    conn.close()

    # Check if the logged-in user is viewing their own profile
    is_own_profile = 'user_id' in session and session['user_id'] == user_id

    # The same profile template is used, but with a context flag that determines what to display
    return render_template('profile.html', user=profile_user, listings=listings, average_rating=average_rating, is_own_profile=is_own_profile)

@app.route('/profile_reviews/<int:user_id>')
def profile_reviews(user_id):
    conn = sqlite3.connect('final.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT Review.*, Users.user_name
        FROM Review
        JOIN Users ON Users.user_id = Review.reviewerID
        WHERE reviewedUserID = ?""", (user_id,))
    reviews = cursor.fetchall()

    return render_template('profile_reviews.html', reviews=reviews)

@app.route('/submit_review/<int:user_id>', methods=['POST'])
def submit_review(user_id):
    reviewer_id = session.get('user_id')
    if reviewer_id is None:
        return redirect(url_for('login'))

    rating = request.form['rating']
    comment = request.form['comment']

    conn = sqlite3.connect('final.db')
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO Review (reviewerID, reviewedUserID, rating, comment)
        VALUES (?, ?, ?, ?)
    """, (reviewer_id, user_id, rating, comment))
    conn.commit()
    conn.close()

    return redirect(url_for('public_profile', user_id=user_id))

@app.route('/user/<int:user_id>/reviews')
def user_reviews(user_id):
    # Retrieve all reviews for the given user
    reviews = get_all_reviews_for_user(user_id)  # You need to define this function
    return render_template('user_reviews.html', reviews=reviews)

def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'jpeg.webp'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_all_reviews_for_user(user_id):
    conn = sqlite3.connect('final.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT Review.*, Users.user_name
        FROM Review
        JOIN Users ON Users.user_id = Review.reviewerID
        WHERE reviewedUserID = ?
    """, (user_id,))

    reviews = cursor.fetchall()
    conn.close()
    return reviews

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)
