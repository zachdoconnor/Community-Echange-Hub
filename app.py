from flask import Flask, render_template, request, redirect, url_for, flash, session
import sqlite3

app = Flask(__name__)
app.secret_key = 'Team6IsHot'  # Change this to a secure random key

# Create a SQLite database connection
conn = sqlite3.connect('final.db')
cursor = conn.cursor()

@app.route('/registration')
def index():
    return render_template('register.html')

@app.route('/register', methods=['POST'])
def register():
    username = request.form['username']
    password = request.form['password']

    if not username or not password:
        flash('Username and password are required', 'error')
        return redirect(url_for('index'))

    conn = sqlite3.connect('final.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO Users (user_name, user_password) VALUES (?, ?)", (username, password))
    conn.commit()
    conn.close()

    flash('Registration successful', 'success')
    return redirect(url_for('index'))

@app.route('/')
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if not username or not password:
            flash('Username and password are required', 'error')
            return redirect(url_for('login'))

        conn = sqlite3.connect('final.db')
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Users WHERE user_name=?", (username,))
        user = cursor.fetchone()
        conn.close()

        if user is None or user[3] != password:
            flash('Invalid username or password', 'error')
        else:
            session['user_id'] = user[0]
            flash('Login successful', 'success')
            return redirect(url_for('profile'))

    return render_template('login.html')

@app.route('/profile')
def profile():
    user_id = session.get('user_id')
    if user_id is None:
        flash('Please log in to access your profile', 'error')
        return redirect(url_for('login'))

    conn = sqlite3.connect('final.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Users WHERE user_id=?", (user_id,))
    user = cursor.fetchone()
    conn.close()

    if user is None:
        flash('User not found', 'error')
        return redirect(url_for('login'))

    return render_template('profile.html', user=user)



@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('Logged out successfully', 'success')
    return redirect(url_for('index'))

@app.route('/update_profile', methods=['POST'])
def update_profile():
    user_id = session.get('user_id')
    if user_id is None:
        flash('Please log in to update your profile', 'error')
        return redirect(url_for('login'))

    email = request.form['email']
    location = request.form['location']
    profile_image = request.form['profile_image']

    conn = sqlite3.connect('final.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE Users SET email=?, location=?, profile_image=? WHERE user_id=?", (email, location, profile_image, user_id))
    conn.commit()
    conn.close()

    flash('Profile updated successfully', 'success')
    return redirect(url_for('profile'))


if __name__ == '__main__':
    app.run(debug=True)
